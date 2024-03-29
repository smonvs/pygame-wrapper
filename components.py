from abc import ABC
from util import *
from exceptions import *
    
class Component(ABC):
    
    def __init__(self, entity):
        self.is_active = True
        self._entity = entity
        self.has_started = False
        
    def initialize(self):
        pass
    
    def start(self):
        pass
    
    def update(self, scene_manager, frame_metrics, input, camera):
        pass
    
    def draw(self, buffer):
        pass
    
    def get_entity(self):
        return self._entity
    
class Transform(Component):
    
    def initialize(self):
        self._position = (0, 0)
        self._prev_position = (0, 0)
        self._scale = (1, 1)
    
    def start(self):
        self._prev_position = self._position
    
    def update(self, scene_manager, delta_time, input, camera):
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
    
    def move_to_direction(self, direction):
        self._position = (self._position[0] + direction[0], self._position[1] + direction[1])
    
    def get_scale(self):
        return self._scale
    
    def set_scale(self, scale):
        self._scale = scale
    
class SpriteRenderer(Component):
    
    def initialize(self):
        self._path = ""
        self._layer = ""
        self._added_to_group = False
        self._flip_x = False
        self._flip_y = False
        self._sprite = None
        
    def start(self):
        self._sprite = pygame.sprite.Sprite()
        self._sprite.image = pygame.image.load(self._path.path).convert_alpha()

    def draw(self, buffer):
        image = self._sprite.image        
        scale = self._entity.transform.get_scale()
        size = image.get_size()
        
        if scale != (1, 1):
            image = pygame.transform.scale(image, (size[0] * scale[0], size[1] * scale[1]))
        
        if not self._added_to_group:
            buffer.add_to_group(self)
            self._added_to_group = True
        
    def get_sprite(self):
        return self._sprite
        
    def set_layer(self, layer):
        self._layer = layer

    def get_layer(self):
        return self._layer

    def set_path(self, path):
        self._path = Path(path)
        
        if self.has_started:
            self._sprite.image = pygame.image.load(self._path.path).convert_alpha()
            
    def flip_x(self, bool):
        self._flip_x = bool      
        self._sprite.image = pygame.transform.flip(self._sprite.image, self._flip_x, self._flip_y)
        
    def flip_y(self, bool):
        self._flip_y = bool
        self._sprite.image = pygame.transform.flip(self._sprite.image, self._flip_x, self._flip_y)
        
class SpriteCollider(Component):
    
    def initialize(self):
        if not self._entity.has_component(SpriteRenderer):
            self._entity.add_component(SpriteRenderer)
            
        self._check_automatically = True
        
    def get_check_automatically(self):
        return self._check_automatically
    
    def set_check_automatically(self, bool):
        self._check_automatically = bool

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
    
    def start(self):
        self._sprite = self._entity.get_component(SpriteRenderer)
        self._default_image = self._sprite.get_sprite()
    
    def update(self, scene_manager, frame_metrics, input, camera):
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
            self._sprite.set_path(self._current_animation.sprites[self._current_index].path)
    
    def add_animation(self, name, fps, paths):
        if name in self._animations:
            raise DuplicateKeyException()

        sprites = []
        for path in paths:
            sprites.append(Path(path))
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
        self._sprite.set_path(self._current_animation.sprites[0].path)
    
    def stop_animation(self):
        self._current_animation = None
        self._animate = False
        self._frame_time = 0
        self._progress = 0
        self._current_index = 0
        self._repeat = False
        self._sprite.set_path(self._default_sprite.path)
    
class Animation:
    
    def __init__(self, sprites, fps):
        self.sprites = sprites
        self.fps = fps