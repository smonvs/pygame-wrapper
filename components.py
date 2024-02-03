from abc import ABC
from exceptions import *
from util import *
import pygame


class Component(ABC):
    
    def __init__(self, entity):
        self.is_active = True
        self._entity = entity
        self.has_started = False
        
    def initialize(self):
        pass
    
    def start(self):
        pass
    
    def update(self, scene_manager, frame_metrics, input):
        pass
    
    def draw(self, buffer):
        pass
    
class Transform(Component):
    
    def initialize(self):
        self._position = (0, 0)
        self._prev_position = (0, 0)
        self._scale = (1, 1)
    
    def start(self):
        self._prev_position = self._position
    
    def update(self, scene_manager, delta_time, input):
        self._prev_position = self._position
        
        if self._entity.get_parent() is not None:
            parent = self._entity.get_parent()
            parent_pos = parent.transform.get_position()
            parent_prev_pos = parent.transform.get_prev_position()
            
            if parent_pos != parent_prev_pos:
                delta_pos = (parent_pos[0] - parent_prev_pos[0], parent_pos[1] - parent_prev_pos[1])
                self.move_to_direction(delta_pos[0], delta_pos[1])            
    
    def get_position(self):
        return self._position
    
    def get_prev_position(self):
        return self._prev_position
    
    def move_to(self, new_position):
        self._position = new_position    
    
    def move_to_direction(self, x, y):
        self._position = (self._position[0] + x, self._position[1] + y)
    
    def get_scale(self):
        return self._scale
    
    def scale(self, x, y):
        self._scale = (x, y)
    
class SpriteRenderer(Component):
    
    def initialize(self):
        self._sprite = None
        self._size = ()
        self._layer = ""
        self._flip_x = False
        self._flip_y = False
        
    def draw(self, buffer):
        scale = self._entity.transform.get_scale()
        sprite = self._sprite

        if self._entity.transform.get_scale() != (1, 1):
            sprite = pygame.transform.scale(self._sprite.get_surface(), (self._size[0] * scale[0], self._size[1] * scale[1]))

        if self._flip_x or self._flip_y:
            sprite = pygame.transform.flip(self._sprite.get_surface(), self._flip_x, self._flip_y)

        buffer.add_to_layer(self._layer, sprite.get_surface(), self._entity.transform.get_position())

    def get_sprite(self):
        return self._sprite

    def set_sprite(self, path):
        self._sprite = Image(path)
        self._size = self._sprite.get_surface().get_rect().size
    
    def set_sprite_image(self, image):
        self._sprite = image.copy()
        self._size = self._sprite.get_surface().get_rect().size
    
    def get_layer(self):
        return self._layer
    
    def set_layer(self, layer):
        self._layer = layer
    
    def flip(self, bool_x, bool_y):
        self._flip_x = bool_x
        self._flip_y = bool_y
            
class SpriteAnimator(Component):
    
    def initialize(self):
        if not self._entity.has_component(SpriteRenderer):
            self._entity.add_component(SpriteRenderer)
        
        self._animations = {}
        self._current_animation = None
        self._animate = False
        self._frame_time = 0
        self._progress = 0
        self._current_index = 0
        self._repeat = False
        self._sprite = self._entity.get_component(SpriteRenderer)
        self._default_sprite = self._sprite.get_sprite()
    
    def update(self, scene_manager, frame_metrics, input):
        if self._animate:
            self._progress += frame_metrics.get_delta_time()
            if self._progress >= self._frame_time:
                self._progress -= self._frame_time
                if self._current_index == len(self._current_animation.sprites) - 1:
                    if self._repeat:
                        self._current_index = 0
                    else:
                        self.stop_animation()
                else:
                    self._current_index += 1
            self._sprite.set_sprite_image(self._current_animation.sprites[self._current_index])
    
    def add_animation(self, name, fps, paths):
        if name in self._animations:
            raise DuplicateKeyException()

        sprites = []
        for path in paths:
            sprites.append(Image(path))
        self._animations[name] = Animation(sprites, fps)
    
    def switch_animation(self, name, repeat):
        if name not in self._animations:
            raise KeyNotFoundException()
        
        self._current_animation = self._animations[name]
        self._animate = True
        self._frame_time = 1 / self._current_animation.fps
        self._progress = 0
        self._current_index = 0
        self._repeat = repeat
        self._sprite.set_sprite_image(self._current_animation.sprites[0])
    
    def stop_animation(self):
        self._current_animation = None
        self._animate = False
        self._frame_time = 0
        self._progress = 0
        self._current_index = 0
        self._repeat = False
        self._sprite.set_sprite_image(self._default_sprite)
    
class Animation:
    
    def __init__(self, sprites, fps):
        self.sprites = sprites
        self.fps = fps