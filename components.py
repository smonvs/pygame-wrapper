from abc import ABC
from exceptions import *
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
    
    def update(self, delta_time, input):
        pass
    
    def draw(self, buffer):
        pass
    
class Transform(Component):
    
    def initialize(self):
        self.__position = (0, 0)
        self.__prev_position = (0, 0)
        self.__scale = (1, 1)
    
    def start(self):
        self.__prev_position = self.__position
    
    def update(self, delta_time, input):
        self.__prev_position = self.__position
        
        if self._entity.get_parent() is not None:
            parent = self._entity.get_parent()
            parent_pos = parent.transform.get_position()
            parent_prev_pos = parent.transform.get_prev_position()
            
            if parent_pos != parent_prev_pos:
                delta_pos = (parent_pos[0] - parent_prev_pos[0], parent_pos[1] - parent_prev_pos[1])
                self.move_to_direction(delta_pos[0], delta_pos[1])            
    
    def get_position(self):
        return self.__position
    
    def get_prev_position(self):
        return self.__prev_position
    
    def move_to(self, new_position):
        self.__position = new_position    
    
    def move_to_direction(self, x, y):
        self.__position = (self.__position[0] + x, self.__position[1] + y)
    
    def get_scale(self):
        return self.__scale
    
    def scale(self, x, y):
        self.__scale = (x, y)
    
class Sprite(Component):
    
    def initialize(self):
        self.__sprite = None
        self.__size = ()
        self.__layer = ""
        self.__flip_x = False
        self.__flip_y = False
        
    def draw(self, buffer):
        scale = self._entity.transform.get_scale()
        sprite = self.__sprite

        if self._entity.transform.get_scale() != (1, 1):
            sprite = pygame.transform.scale(self.__sprite, (self.__size[0] * scale[0], self.__size[1] * scale[1]))

        if self.__flip_x or self.__flip_y:
            sprite = pygame.transform.flip(sprite, self.__flip_x, self.__flip_y)

        buffer.add_to_layer(self.__layer, sprite, self._entity.transform.get_position())

    def get_sprite(self):
        return self.__sprite

    def set_sprite(self, path):
        self.__sprite = pygame.image.load(path)
        self.__sprite = self.__sprite.convert_alpha()
        self.__size = self.__sprite.get_rect().size
    
    def set_sprite_image(self, image):
        self.__sprite = image
        self.__sprite = self.__sprite.convert_alpha()
        self.__size = self.__sprite.get_rect().size
    
    def get_layer(self):
        return self.__layer
    
    def set_layer(self, layer):
        self.__layer = layer
    
    def flip(self, bool_x, bool_y):
        self.__flip_x = bool_x
        self.__flip_y = bool_y
            
class SpriteAnimator(Component):
    
    def initialize(self):
        if not self._entity.has_component(Sprite):
            self._entity.add_component(Sprite)
        
        self.__animations = {}
        self.__current_animation = None
        self.__animate = False
        self.__frame_time = 0
        self.__progress = 0
        self.__current_index = 0
        self.__repeat = False
        self.__sprite = self._entity.get_component(Sprite)
        self.__default_sprite = self.__sprite.get_sprite()
    
    def update(self, frame_metrics, input):
        if self.__animate:
            self.__progress += frame_metrics.get_delta_time()
            if self.__progress >= self.__frame_time:
                self.__progress -= self.__frame_time
                if self.__current_index == len(self.__current_animation.sprites) - 1:
                    if self.__repeat:
                        self.__current_index = 0
                    else:
                        self.stop_animation()
                else:
                    self.__current_index += 1
            self.__sprite.set_sprite_image(self.__current_animation.sprites[self.__current_index])
    
    def add_animation(self, name, fps, paths):
        if name in self.__animations:
            raise DuplicateKeyException()

        sprites = []
        for path in paths:
            sprites.append(pygame.image.load(path))
        self.__animations[name] = Animation(sprites, fps)
    
    def switch_animation(self, name, repeat):
        if name not in self.__animations:
            raise KeyNotFoundException()
        
        self.__current_animation = self.__animations[name]
        self.__animate = True
        self.__frame_time = 1 / self.__current_animation.fps
        self.__progress = 0
        self.__current_index = 0
        self.__repeat = repeat
        self.__sprite.set_sprite_image(self.__current_animation.sprites[0])
    
    def stop_animation(self):
        self.__current_animation = None
        self.__animate = False
        self.__frame_time = 0
        self.__progress = 0
        self.__current_index = 0
        self.__repeat = False
        self.__sprite.set_sprite_image(self.__default_sprite)
    
class Animation:
    
    def __init__(self, sprites, fps):
        self.sprites = sprites
        self.fps = fps