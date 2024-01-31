from typing import Type, TypeVar
from abc import ABC, abstractmethod
from exceptions import *
from components import *
from util import *
import time
import pygame
import copy
import os

T = TypeVar("T", bound = Component)

class Game(ABC):
    
    def __init__(self, px_width, px_height, title, frame_limit):
        self._px_width = px_width
        self._px_height = px_height
        self._title = title
        self._frame_limit = frame_limit
        self._input = Input()
        self._buffer = Buffer(px_width, px_height)
        self._frame_metrics = Frame_Metrics()
        self._running = True
        self._scenes = {}
        self._current_scene = None
    
    def run(self):        
        self._initialize()
        self._load_content()
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
        self._current_scene.update_entities(self._frame_metrics, self._input)
    
    def _draw_scene(self):
        self._current_scene.draw_entities(self._buffer)
    
    def _add_scene(self, name):
        if self._get_scene(name) is not None:
            raise DuplicateSceneException()

        new_scene = Scene(name)
        self._scenes[name] = new_scene
        log("Added new (P)Scene(/) (C)" + name + "(/)")
        return new_scene
    
    def _get_scene(self, name):
        scene = self._scenes.get(name, None)
        if scene is not None:
            return scene
        else:
            return None
    
    def _change_scene(self, name):
        scene = self._get_scene(name)
        if scene is None:
            raise SceneNotFoundException()
        
        self._current_scene = scene.copy()

class Scene:
    
    def __init__(self, name):
        self.__name = name
        self.__entities = {}
    
    def get_name(self):
        return self.__name
    
    def add_entity(self, name, parent):
        if self.get_entity(name) is not None:
            raise DuplicateEntityException()
        
        new_entity = Entity(name, self, parent) 
        self.__entities[name] = new_entity
        
        if parent is not None:
            log("Added new (P)Entity(/) (C)" + name + "(/) to (P)Scene(/) (C)" + self.__name + "(/) as child of (P)Entity(/) (C)" + parent.get_name() + "(/)")
        else:
            log("Added new (P)Entity(/) (C)" + name + "(/) to (P)Scene(/) (C)" + self.__name + "(/)")      
        
        transform = new_entity.add_component(Transform)
        new_entity.transform = transform
        return new_entity
    
    def get_entity(self, name):
        entity = self.__entities.get(name, None)
        if entity is not None:
            return entity
        else:
            return None
    
    def copy_entities(self):
        return self.__entities.copy()
    
    def paste_entities(self, entities):
        self.__entities = entities
    
    def update_entities(self, frame_metrics, input):
        for entity_name, entity in self.__entities.items():
            if entity.is_hierarchy_active():
                entity.update_components(frame_metrics, input)
    
    def draw_entities(self, buffer):
        for entity_name, entity in self.__entities.items():
            if entity.is_hierarchy_active() and entity.is_hierarchy_visible():
                entity.draw_components(buffer)
            
    def copy(self):
        copied_scene = Scene("CURRENT")
        copied_scene.paste_entities(self.copy_entities())
        return copied_scene

class Entity:
    
    def __init__(self, name, scene, parent):
        self.is_active = True
        self.is_visible = True
        self.__name = name
        self.__scene = scene
        self.__parent = parent
        self.__children = {}
        self.__components = []

    def get_name(self):
        return self.__name

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
        return self.__parent

    def get_child(self, name):
        child = self.__children.get(name)
        if child is not None and child in self.__children:
                return child
        return None
    
    def get_children(self):
        return self.__children

    def add_component(self, component: Type[T]) -> T:
        if self.get_component(component) is not None:
            raise DuplicateComponentException()

        new_component = component(self)
        new_component.initialize()
        self.__components.append(new_component)
        log("Added (P)Component(/) of type (C)" + new_component.__class__.__name__ + "(/) to (P)Entity(/) (C)" + self.__name + "(/)")
        return new_component 

    def get_component(self, component: Type[T]) -> T:
        for comp in self.__components:
            if isinstance(comp, component):
                return comp
        return None

    def has_component(self, component: Type[T]) -> T:
        if self.get_component(component) is None:
            return False
        else:
            return True

    def update_components(self, frame_metrics, input):
        for component in self.__components:
            if component.is_active:
                if not component.has_started:
                    component.start()
                    component.has_started = True
                component.update(frame_metrics, input)

    def draw_components(self, buffer):
        for component in self.__components:
            if component.is_active:   
                component.draw(buffer)

class Buffer:
    
    def __init__(self, px_width, px_height):
        self.__buffer_surface = pygame.Surface((px_width, px_height))
        self.__layers = {}
        
    def create_layer(self, name):
        if name in self.__layers:
            raise DuplicateBufferLayerException()
        
        self.__layers[name] = []
        log("Created (P)Bufferlayer(/) (C)" + name + "(/)")
                        
    def add_to_layer(self, layer, content, position):
        if layer not in self.__layers:
            raise UnknownBufferLayerException()
        
        self.__layers[layer].append(Buffer_Data(content, position))

    def draw(self):
        for layer, data_list in self.__layers.items():
            blit_data = [(data.content, data.position) for data in data_list]
            self.__buffer_surface.blits(blit_data)
            self.__layers[layer] = []

    def get_surface(self):
        return self.__buffer_surface

    def clear(self):
        self.__buffer_surface.fill(Color.BLACK)

class Buffer_Data:
    
    def __init__(self, content, position):
        self.content = content
        self.position = position

class Input:
    
    def __init__(self):
        self.__key_states = {}
        self.__prev_key_states = {}
        self.__mouse_pos = (0, 0)
        self.__mouse_wheel = 0
        self.__mouse_states = {}
        self.__prev_mouse_states = {}

    def copy_prev(self):
        self.__mouse_wheel = 0
        self.__prev_key_states = self.__key_states.copy()
        self.__prev_mouse_states = self.__mouse_states.copy()

    def update_keydown(self, key):
        self.__key_states[key] = True

    def update_keyup(self, key):
        self.__key_states[key] = False

    def update_mouse_pos(self):
        self.__mouse_pos = pygame.mouse.get_pos()

    def update_mouse_pressed(self, button):
        self.__mouse_states[button] = True
    
    def update_mouse_released(self, button):
        self.__mouse_states[button] = False

    def update_mouse_wheel(self, direction):
        self.__mouse_wheel = direction
        
    def is_key_pressed(self, key):
        return self.__key_states.get(key, False)

    def is_key_just_pressed(self, key):
        return self.__key_states.get(key, False) and not self.__prev_key_states.get(key, False)

    def is_key_just_released(self, key): 
        return not self.__key_states.get(key, False) and self.__prev_key_states.get(key, False)

    def get_mouse_pos(self):
        return self.__mouse_pos
    
    def get_mouse_wheel(self):
        return self.__mouse_wheel
    
    def is_mouse_pressed(self, button):
        return self.__mouse_states.get(button, False)

    def is_mouse_just_pressed(self, button):
        return self.__mouse_states.get(button, False) and not self.__prev_mouse_states.get(button, False)
    
    def is_mouse_just_released(self, button):
        return not self.__mouse_states.get(button, False) and self.__prev_mouse_states.get(button, False)
    
class Frame_Metrics:
    
    def __init__(self):
        self.__start_time = None
        self.__end_time = 0
        self.__delta_time = 0
    
    def start(self):
        self.__start_time = time.time()
    
    def update(self):
        self.__end_time = time.time()
        self.__delta_time = self.__end_time - self.__start_time
        self.__start_time = time.time()
        
    def get_delta_time(self):
        return self.__delta_time