from typing import Type, TypeVar
from abc import ABC, abstractmethod
from exceptions import *
from components import *
from util import *
from components_custom import *
import time
import pygame

T = TypeVar("T", bound = Component)
debug = True

class Game(ABC):
    
    def __init__(self, px_width, px_height, title, frame_limit):
        self._px_width = px_width
        self._px_height = px_height
        self._title = title
        self._frame_limit = frame_limit
        self._input = Input()
        self._buffer = Buffer(px_width, px_height)
        self._frame_metrics = FrameMetrics()
        self._running = True
        self._scenes = {}
        self._current_scene = None
        self._scene_builder = SceneBuilder()
        self._scene_manager = SceneManager()
    
    def run(self):        
        self._initialize()
        self._load_content(self._scene_builder)
        self._scene_builder.save_scenes_as_files()
        self._gameloop()
    
    def _initialize(self):
        pygame.init()
        pygame.display.set_caption(self._title)
        self._window = pygame.display.set_mode((self._px_width, self._px_height))

    @abstractmethod
    def _load_content(self):
        pass
    
    def _gameloop(self):
        self._frame_metrics.start()    
        pygame_clock = pygame.time.Clock()
        
        while self._running:
            self._window.fill(Color.BLACK)
            self._input.copy_prev()
            self._handle_events()
            self._update_scene()
            self._draw_scene()
            self._buffer.draw()
            self._window.blit(self._buffer.get_surface(), (0, 0))
            pygame.display.update()
            self._buffer.clear()
            self._frame_metrics.update()
            pygame_clock.tick(self._frame_limit)
        
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                pygame.quit()
            elif event.type == pygame.KEYDOWN:
                self._input.update_keydown(event.key)
            elif event.type == pygame.KEYUP:
                self._input.update_keyup(event.key)
            elif event.type == pygame.MOUSEMOTION:
                self._input.update_mouse_pos()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._input.update_mouse_pressed(event.button)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._input.update_mouse_released(event.button)
            elif event.type == pygame.MOUSEWHEEL:
                self._input.update_mouse_wheel(event.y)
    
    def _update_scene(self):
        self._scene_manager.get_current_scene().update_entities(self._scene_manager, self._frame_metrics, self._input)
    
    def _draw_scene(self):
        self._scene_manager.get_current_scene().draw_entities(self._buffer)

class SceneBuilder:
    
    def __init__(self):
        self._scenes = {} 

    def create_scene(self, name, is_main):
        if name in self._scenes:
            raise DuplicateSceneException()
        
        new_scene = Scene(name, is_main)
        self._scenes[name] = new_scene
        return new_scene

    def save_scenes_as_files(self):
        for scene_name, scene in self._scenes.items():
            with open(f"res/{scene_name}.pyscn", "w") as file:
                line = f"scene name='{scene_name}' is_main={scene._is_main}"
                file.write(line)
                
                for entity_name, entity in scene._entities.items():
                    if entity._parent != None:
                        parent = f"'{entity._parent.get_name()}'"
                    else:
                        parent = "null"                   
                    
                    line = f"entity name='{entity_name}' is_active={entity.is_active} is_visible={entity.is_visible} parent={parent}"
                    file.write(f"\n{line}")
                    
                    for component in entity._components:
                        line = f"component type={component.__class__.__name__}"
                        
                        for attr, value in component.__dict__.items():
                            if attr != "_entity" and attr != "has_started" and not issubclass(type(value), Component):
                                value = self._recursive_get_attr(value)                            
                                line += f" {attr}={value}"
                            
                        file.write(f"\n{line}")
                    
    def _recursive_get_attr(self, value):
        if isinstance(value, dict):
            return {key: self._recursive_get_attr(val) for key, val in value.items()}
        elif isinstance(value, list):
            return [self._recursive_get_attr(item) for item in value]
        elif isinstance(value, (int, bool, float, str, tuple)):
            return value
        elif isinstance(value, type(None)):
            return "null"
        elif isinstance(value, Image):
            return f"/'{value.get_path()}'"
        else:
            return f"#{value.__class__.__name__}#{self._recursive_get_attr(value.__dict__)}"
        
                    
    def clear_files(self):
        pass

class SceneManager:
    
    def __init__(self):
        self._current_scene = None
    
    def get_current_scene(self):
        return self._current_scene
    
    def switch_scene(self, name):
        pass

class Scene:
    
    def __init__(self, name, is_main):
        self._name = name
        self._entities = {}
        self._is_main = is_main
    
    def get_name(self):
        return self._name
    
    def add_entity(self, name, parent):
        if self.get_entity(name) is not None:
            raise DuplicateEntityException()
        
        new_entity = Entity(name, self, parent) 
        self._entities[name] = new_entity
        
        if debug:
            if parent is not None:
                log("Added new (P)Entity(/) (C)" + name + "(/) to (P)Scene(/) (C)" + self._name + "(/) as child of (P)Entity(/) (C)" + parent.get_name() + "(/)")
            else:
                log("Added new (P)Entity(/) (C)" + name + "(/) to (P)Scene(/) (C)" + self._name + "(/)")      
            
        transform = new_entity.add_component(Transform)
        new_entity.transform = transform
        return new_entity
    
    def get_entity(self, name):
        entity = self._entities.get(name, None)
        if entity is not None:
            return entity
        else:
            return None
    
    def update_entities(self, scene_manager, frame_metrics, input):
        for entity_name, entity in self._entities.items():
            if entity.is_hierarchy_active():
                entity.update_components(scene_manager, frame_metrics, input)
    
    def draw_entities(self, buffer):
        for entity_name, entity in self._entities.items():
            if entity.is_hierarchy_active() and entity.is_hierarchy_visible():
                entity.draw_components(buffer)

class Entity:
    
    def __init__(self, name, scene, parent):
        self.is_active = True
        self.is_visible = True
        self._name = name
        self._scene = scene
        self._parent = parent
        self._children = {}
        self._components = []

    def get_name(self):
        return self._name

    def is_hierarchy_active(self):
        entity = self
        while entity is not None:
            if not entity.is_active:
                return False
            entity = entity.get_parent()
        return True
     
    def is_hierarchy_visible(self):
        entity = self
        while entity is not None:
            if not entity.is_visible:
                return False
            entity = entity.get_parent()
        return True

    def get_parent(self):
        return self._parent

    def get_child(self, name):
        child = self._children.get(name)
        if child is not None and child in self._children:
                return child
        return None
    
    def get_children(self):
        return self._children

    def add_component(self, component: Type[T]) -> T:
        if self.get_component(component) is not None:
            raise DuplicateComponentException()

        new_component = component(self)
        new_component.initialize()
        self._components.append(new_component)
        
        if debug:
            log("Added (P)Component(/) of type (C)" + new_component.__class__.__name__ + "(/) to (P)Entity(/) (C)" + self._name + "(/)")
        
        return new_component 

    def get_component(self, component: Type[T]) -> T:
        for comp in self._components:
            if isinstance(comp, component):
                return comp
        return None

    def has_component(self, component: Type[T]) -> T:
        if self.get_component(component) is None:
            return False
        else:
            return True

    def update_components(self, scene_manager, frame_metrics, input):
        for component in self._components:
            if component.is_active:
                if not component.has_started:
                    component.start()
                    component.has_started = True
                component.update(scene_manager, frame_metrics, input)

    def draw_components(self, buffer):
        for component in self._components:
            if component.is_active:   
                component.draw(buffer)

class Buffer:
    
    _layers = {}
    
    def __init__(self, px_width, px_height):
        self._buffer_surface = pygame.Surface((px_width, px_height))
        
    @staticmethod
    def create_layer(name):
        if name in Buffer._layers:
            raise DuplicateBufferLayerException()
        
        Buffer._layers[name] = []
        log("Created (P)Bufferlayer(/) (C)" + name + "(/)")
                        
    def add_to_layer(self, layer, content, position):
        if layer not in self._layers:
            raise UnknownBufferLayerException()
        
        self._layers[layer].append(BufferData(content, position))

    def draw(self):
        for layer, data_list in Buffer._layers.items():
            blit_data = [(data.content, data.position) for data in data_list]
            self._buffer_surface.blits(blit_data)
            self._layers[layer] = []

    def get_surface(self):
        return self._buffer_surface
            
    def clear(self):
        self._buffer_surface.fill(Color.BLACK)

class BufferData:
    
    def __init__(self, content, position):
        self.content = content
        self.position = position

class Input:
    
    def __init__(self):
        self._key_states = {}
        self._prev_key_states = {}
        self._mouse_pos = (0, 0)
        self._mouse_wheel = 0
        self._mouse_states = {}
        self._prev_mouse_states = {}

    def copy_prev(self):
        self._mouse_wheel = 0
        self._prev_key_states = self._key_states.copy()
        self._prev_mouse_states = self._mouse_states.copy()

    def update_keydown(self, key):
        self._key_states[key] = True

    def update_keyup(self, key):
        self._key_states[key] = False

    def update_mouse_pos(self):
        self._mouse_pos = pygame.mouse.get_pos()

    def update_mouse_pressed(self, button):
        self._mouse_states[button] = True
    
    def update_mouse_released(self, button):
        self._mouse_states[button] = False

    def update_mouse_wheel(self, direction):
        self._mouse_wheel = direction
        
    def is_key_pressed(self, key):
        return self._key_states.get(key, False)

    def is_key_just_pressed(self, key):
        return self._key_states.get(key, False) and not self._prev_key_states.get(key, False)

    def is_key_just_released(self, key): 
        return not self._key_states.get(key, False) and self._prev_key_states.get(key, False)

    def get_mouse_pos(self):
        return self._mouse_pos
    
    def get_mouse_wheel(self):
        return self._mouse_wheel
    
    def is_mouse_pressed(self, button):
        return self._mouse_states.get(button, False)

    def is_mouse_just_pressed(self, button):
        return self._mouse_states.get(button, False) and not self._prev_mouse_states.get(button, False)
    
    def is_mouse_just_released(self, button):
        return not self._mouse_states.get(button, False) and self._prev_mouse_states.get(button, False)
    
class FrameMetrics:
    
    def __init__(self):
        self._start_time = None
        self._end_time = 0
        self._delta_time = 0
    
    def start(self):
        self._start_time = time.time()
    
    def update(self):
        self._end_time = time.time()
        self._delta_time = self._end_time - self._start_time
        self._start_time = time.time()
        
    def get_delta_time(self):
        return self._delta_time