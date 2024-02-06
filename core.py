from typing import Type, TypeVar
from abc import ABC, abstractmethod
from exceptions import *
from util import *
from components import * 
from components_custom import *
from pygame.locals import DOUBLEBUF
import time
import pygame
import shutil
import os
import inspect

class Game(ABC):
    
    px_width = 0
    px_height = 0
    
    def __init__(self, px_width, px_height, title, frame_limit):
        self._px_width = px_width
        self._px_height = px_height
        Game.px_width = px_width
        Game.px_height = px_height
        self._title = title
        self._frame_limit = frame_limit
        self._input = Input()
        self._frame_metrics = FrameMetrics()
        self._running = True
        self._scenes = {}
        self._current_scene = None
        self._scene_builder = SceneBuilder()
    
    def run(self):        
        self._initialize()
        self._load_content(self._scene_builder, self._buffer)
        self._scene_builder.save_scenes_as_files()
        self._gameloop()
        self._unload_content()
    
    def _initialize(self):
        pygame.init()
        pygame.display.set_caption(self._title)
        self._window = pygame.display.set_mode((self._px_width, self._px_height), DOUBLEBUF)
        self._buffer = Buffer(self._window)
        self._scene_manager = SceneManager(self._buffer)

    @abstractmethod
    def _load_content(self, scene_builder, buffer):
        pass
    
    def _gameloop(self):
        self._frame_metrics.start()    
        pygame_clock = pygame.time.Clock()
        
        self._scene_manager.switch_scene(self._scene_builder.main_scene)
        
        while self._running:
            self._input.copy_prev()
            self._handle_events()
            if not self._running: break
            self._update_scene()
            self._draw_scene()
            self._buffer.draw()
            pygame.display.flip()
            self._frame_metrics.update()
            pygame_clock.tick(self._frame_limit)
            print(pygame_clock.get_fps())
        
    def _unload_content(self):
        shutil.rmtree("tmp")
        
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
                self._input.update_mouse_ptmpsed(event.button)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._input.update_mouse_released(event.button)
            elif event.type == pygame.MOUSEWHEEL:
                self._input.update_mouse_wheel(event.y)
    
    def _update_scene(self):
        self._scene_manager.get_current_scene().update_entities(self._scene_manager, self._frame_metrics, self._input, self._buffer._camera)
        self._scene_manager.get_current_scene().check_entities_for_deletion()
    
    def _draw_scene(self):
        self._scene_manager.get_current_scene().draw_entities(self._buffer)

    def get_window(self):
        return self._window

    
T = TypeVar("T", bound = Component)

class SceneBuilder:
    
    def __init__(self):
        self._scenes = {} 
        self.main_scene = ""

    def create_scene(self, name, is_main):
        if name in self._scenes:
            raise DuplicateSceneException()
        
        new_scene = Scene(name, is_main)
        self._scenes[name] = new_scene
        return new_scene

    def save_scenes_as_files(self):
        if os.path.exists("tmp"):        
            shutil.rmtree("tmp")
        
        os.makedirs("tmp")
        
        for scene_name, scene in self._scenes.items():
            with open(f"tmp/{scene_name}.pyscn", "w") as file:
                t = "\t"
                file.write("[scene]\n")
                file.write(f"{t}name={scene_name}\n")
                
                file.write(f"{t}camera={scene.camera.get_name()}\n")
                
                if scene._is_main:
                    self.main_scene = scene_name
                
                for entity_name, entity in scene._entities.items():
                    file.write(f"{t}[entity]\n")
                    t = "\t\t"
                    file.write(f"{t}name={entity_name}\n")
                    file.write(f"{t}is_active={entity.is_active}\n")
                    file.write(f"{t}is_visible={entity.is_visible}\n")
                    if entity._parent != None:
                        parent = entity._parent._name
                    else:
                        parent = None
                    file.write(f"{t}parent={parent}\n")
                    
                    for component_type, component in entity._components.items():
                        t = "\t\t"
                        file.write(f"{t}[component]\n")
                        t = "\t\t\t"
                        file.write(f"{t}type={component.__class__.__name__}\n")
                        
                        for attribute, value in component.__dict__.items():
                            if attribute == "_entity" or attribute == "has_started": 
                                continue
                            file.write(f"{t}{attribute}={self._recursive_write_value(attribute, value, t)}\n")
                        
                        t = "\t\t"
                        file.write(f"{t}[/component]\n")
                    
                    t = "\t"
                    file.write(f"{t}[/entity]\n")
                    
                file.write("[/scene]")
                        
        self._scenes = {}
                        
    def _recursive_write_value(self, attribute, value, t):
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        elif isinstance(value, type(None)):
            return "None"
        elif isinstance(value, tuple):
            return value
        elif isinstance(value, Path):
            return f"/{value.path}"
        elif isinstance(value, pygame.Rect):
            return value
        elif isinstance(value, dict): 
            result = "{\n"
            t += "\t"
            dictionary = value
            for key, value in dictionary.items():
                result += f"{t}{key}:{self._recursive_write_value(key, value, t)}\n"
            result += t[:-1] + "}" + attribute
            return result
        elif isinstance(value, list):
            result = "[\n"
            t += "\t"
            list2 = value
            for value in list2:
                result += f"{t}{self._recursive_write_value(None, value, t)}\n"
            result += t[:-1] + "]" + attribute
            return result
        else:       
            object = value
            result = f"[{object.__class__.__name__}]\n"
            t += "\t"
            for key, value in object.__dict__.items():
                result += f"{t}{key}:{self._recursive_write_value(key, value, t)}\n"
            result += t[:-1] + f"[/{object.__class__.__name__}]"
            return result
        
class SceneManager:
    
    def __init__(self, buffer):
        self._current_scene = None
        self._buffer = buffer
    
    def get_current_scene(self):
        return self._current_scene
    
    def switch_scene(self, name):
        scene = None
        
        log(f"Loading (P)Scene(/) (C){name}(/)")
        
        with open(f"tmp/{name}.pyscn", "r") as file:
            file.readline()
            line = file.readline().strip()
            name = line.split("=")[1]
            line = file.readline().strip()
            camera = line.split("=")[1]
            scene = Scene(name, None)
            
            entity = None
            component = None
            
            while True:
                line = file.readline().strip()
                if line == "[entity]":
                    name = file.readline().strip().split("=")[1]
                    is_active = bool(file.readline().strip().split("=")[1])
                    is_visible = bool(file.readline().strip().split("=")[1])
                    parent = file.readline().strip().split("=")[1]
                    
                    if parent != "None":
                        parent = scene.get_entity(parent)
                    else:
                        parent = None
                    
                    entity = scene.add_entity(name, parent)
                    entity.is_active = is_active
                    entity.is_visible = is_visible
                
                elif line == "[component]":
                    type = file.readline().strip().split("=")[1]
                    is_active = bool(file.readline().strip().split("=")[1])
                
                    if type == "Transform":
                        component = entity.get_component(Transform)
                    else:
                        component = entity.add_component(globals()[type])
                    
                    component.is_active = is_active

                elif line == "[/component]":         
                    component = None
                    
                elif line == "[/scene]":
                    break
                
                elif component != None:                    
                    if line.count("=") > 0:
                        attr = line.split("=")
                    else:
                        attr = line.split(":")
                        
                    key = attr[0]
                    value = attr[1]
                
                    component.__dict__[key] = self._set_attr_value(key, value, file)        
        
        self._buffer._camera.main = scene._entities[camera]
        
        log(f"Loaded (P)Scene(/) (C){scene.get_name()}(/) successfully")
        self._current_scene = scene

    def _set_attr_value(self, key, value, file):
        if value == "{":
            dict = {}
            attr_key = key
            while True:
                line = file.readline().strip()
                if line == "}" + attr_key:
                    break
                if line.count("=") > 0:
                    attr = line.split("=")
                else:
                    attr = line.split(":")
                key = attr[0]
                value = attr[1]
                dict[key] = self._set_attr_value(key, value, file)
            return dict
        elif value == "[":
            list = []
            while True:
                line = file.readline().strip()
                if line == "]" + key:
                    break
                list.append(self._set_attr_value(None, line, file))
            return list
        elif value.startswith("("):
            return eval(value)
        elif value.startswith("[") and value.endswith("]"):
            class_name = value[1:-1]
            class_attr = {}
            while True:
                line = file.readline().strip()
                if line == f"[/{class_name}]":
                    break
                if line.count("=") > 0:
                    attr = line.split("=")
                else:
                    attr = line.split(":")
                key = attr[0]
                value = attr[1]
                class_attr[key] = self._set_attr_value(key, value, file)
            return globals()[class_name](**class_attr)
        elif value.startswith("/"):
            return Path(value[1:])
        elif value.isdigit():
            return int(value)
        elif value.replace(".", "", 1).isdigit() and value.count(".") <= 1:
            return float(value)
        elif value == "True":
            return True
        elif value == "False":
            return False
        elif value == "None":
            return None
        else:
            return value

class Scene:
    
    def __init__(self, name, is_main):
        self._name = name
        self._entities = {}
        self._is_main = is_main
        self._to_be_deleted = []
        self.camera = ""
    
    def get_name(self):
        return self._name
    
    def add_entity(self, name, parent):
        if self.get_entity(name) is not None:
            raise DuplicateEntityException()
        
        new_entity = Entity(name, self, parent) 
        self._entities[name] = new_entity
        
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

    def update_entities(self, scene_manager, frame_metrics, input, camera):
        for entity_name, entity in self._entities.items():
            if entity.is_hierarchy_active():
                entity.update_components(scene_manager, frame_metrics, input, camera)
    
    def draw_entities(self, buffer):
        for entity_name, entity in self._entities.items():
            if entity.is_hierarchy_active() and entity.is_hierarchy_visible():
                entity.draw_components(buffer)

    def check_entities_for_deletion(self):
        for key in self._to_be_deleted:
            self._entities.pop(key)
        
        self._to_be_deleted = []
        
class Entity:
    
    def __init__(self, name, scene, parent):
        self.is_active = True
        self.is_visible = True
        self._name = name
        self._scene = scene
        self._parent = parent
        self._children = {}
        self._components = {}

    def delete(self):
        for type, component in self._components.items():
            component.is_active = False
            del component
        
        self._scene._to_be_deleted.append(self._name)
        self.is_active = False
        del self

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
        self._components[component] = (new_component)
        
        log("Added (P)Component(/) of type (C)" + new_component.__class__.__name__ + "(/) to (P)Entity(/) (C)" + self._name + "(/)")
        
        return new_component 

    def get_component(self, component: Type[T]) -> T:
        return self._components.get(component, None)

    def has_component(self, component: Type[T]) -> T:
        if self.get_component(component) is None:
            return False
        else:
            return True

    def update_components(self, scene_manager, frame_metrics, input, camera):
        for type, component in self._components.items():
            if component.is_active:
                if not component.has_started:
                    component.start()
                    component.has_started = True
                component.update(scene_manager, frame_metrics, input, camera)

    def draw_components(self, buffer):
        for type, component in self._components.items():
            if component.is_active:   
                component.draw(buffer)

class Buffer:
        
    def __init__(self, window):
        self._window = window
        self._window_size = self._window.get_size()
        self._buffer_surface = pygame.Surface(self._window_size)
        self._layers = {}
        self._collider_group = {}
        self._camera = Camera()
    
    def add_layer(self, layer):
        if layer not in self._layers:
            self._layers[layer] = []
            self._collider_group[layer] = set()
    
    def add_to_group(self, sprite_renderer):
        layer = sprite_renderer.get_layer()
        
        if layer not in self._layers:
            raise UnknownBufferLayerException()
        
        buffer_data = BufferData(sprite_renderer)
        
        self._layers[layer].append(buffer_data)
        
        if sprite_renderer.get_entity().has_component(SpriteCollider):
            self._collider_group[layer].add(buffer_data)

    def remove_from_group(self, sprite_renderer):
        key = sprite_renderer.get_entity().get_name()
        layer = sprite_renderer.get_layer()
        
        for data in self._layers[layer]:
            if data.key == key:
                self._layers[layer].remove(data)
                self._collider_group[layer].discard(data.collider)
                break

    def draw(self):        
        self._buffer_surface.fill((255, 0, 255))
    
        camera_position = self._camera.main.transform.get_position()
        camera_position = (camera_position[0] - (self._window_size[0] / 2), camera_position[1] - (self._window_size[1] / 2))
        rects = {layer: [data.sprite.image.get_rect() for data in data_list] for layer, data_list in self._layers.items()}

        for layer, data_list in self._layers.items():
            data_list = sorted(data_list, key=lambda data: -data.transform.get_position()[1])
                        
            for i, buffer_data in enumerate(data_list):
                if buffer_data.entity.is_active:
            
                    blit_position = (
                        buffer_data.transform.get_position()[0] - camera_position[0],
                        buffer_data.transform.get_position()[1] - camera_position[1],
                    )        
                    
                    self._buffer_surface.blit(buffer_data.sprite.image, blit_position)
            
            
            self._window.blit(self._buffer_surface, (0, 0))
                            
    def get_surface(self):
        return self._buffer_surface
            
    def clear(self):
        self._buffer_surface.fill(Color.BLACK)

class BufferData:
    
    def __init__(self, sprite_renderer):
        self.entity = sprite_renderer.get_entity()
        self.key = sprite_renderer.get_entity().get_name()
        self.transform = sprite_renderer._entity.transform
        self.sprite = sprite_renderer.get_sprite()
        self.collider = sprite_renderer._entity.get_component(SpriteCollider)

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

    def update_mouse_ptmpsed(self, button):
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
    
class Camera:
    
    def __init__(self):
        self.main = None