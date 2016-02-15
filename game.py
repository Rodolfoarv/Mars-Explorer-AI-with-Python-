SCREEN_SIZE = (600, 600)
NEST_POSITION = (SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2)
ANT_COUNT = 10
ROCK_COUNT = 20
NEST_SIZE = 40.
LEAF_COUNT = 20

import pygame
from pygame.locals import *

from random import randint, choice
from gameobjects.vector2 import Vector2

class State(object):

    def __init__(self, name):
        self.name = name

    def do_actions(self):
        pass

    def check_conditions(self):
        pass

    def entry_actions(self):
        pass

    def exit_actions(self):
        pass


class StateMachine(object):

    def __init__(self):

        self.states = {}
        self.active_state = None


    def add_state(self, state):
        self.states[state.name] = state

    def think(self):

        if self.active_state is None:
            return

        self.active_state.do_actions()
        new_state_name = self.active_state.check_conditions()
        if new_state_name is not None:
            self.set_state(new_state_name)


    def set_state(self, new_state_name):

        if self.active_state is not None:
            self.active_state.exit_actions()

        self.active_state = self.states[new_state_name]
        self.active_state.entry_actions()



class World(object):

    def __init__(self):

        self.entities = {}
        self.entity_id = 0
        self.background = pygame.image.load("grass.png").convert()
        pygame.draw.circle(self.background, (200, 255, 200), NEST_POSITION, int(NEST_SIZE))

    def add_entity(self, entity):

        self.entities[self.entity_id] = entity
        entity.id = self.entity_id
        self.entity_id += 1

    def remove_entity(self, entity):

        del self.entities[entity.id]

    def get(self, entity_id):

        if entity_id in self.entities:
            return self.entities[entity_id]
        else:
            return None

    def process(self, time_passed):

        time_passed_seconds = time_passed / 1000.0
        for entity in self.entities.values():
            entity.process(time_passed_seconds)

    def render(self, surface):

        surface.blit(self.background, (0, 0))
        for entity in self.entities.itervalues():
            entity.render(surface)


    def get_close_entity(self, name, location, range=60.):

        location = Vector2(*location)

        for entity in self.entities.itervalues():
            if entity.name == name:
                distance = location.get_distance_to(entity.location)
                if distance < range:
                    return entity
        return None

    def in_obstacle(self, point, range=16.):
        location = Vector2(*point)
        for entity in self.entities.itervalues():
            if entity.name == "rock":
                distance = location.get_distance_to(entity.location)
                if distance < range:
                    return True
        return False
    def is_inside_nest(self, pos):
        location = Vector2(*pos)
        return Vector2(*NEST_POSITION).get_distance_to(location) < NEST_SIZE

class GameEntity(object):

    def __init__(self, world, name, image):

        self.world = world
        self.name = name
        self.image = image
        self.location = Vector2(0, 0)
        self.destination = Vector2(0, 0)
        self.speed = 0.
        self.brain = StateMachine()
        self.id = 0

    def render(self, surface):

        x, y = self.location
        w, h = self.image.get_size()
        surface.blit(self.image, (x-w/2, y-h/2))

    def process(self, time_passed):

        self.brain.think()

        if self.speed > 0. and self.location != self.destination:

            vec_to_destination = self.destination - self.location
            distance_to_destination = vec_to_destination.get_length()
            heading = vec_to_destination.get_normalized()
            travel_distance = min(distance_to_destination, time_passed * self.speed)
            self.location += travel_distance * heading


class Leaf(GameEntity):

    def __init__(self, world, image):
        GameEntity.__init__(self, world, "leaf", image)
        self.stock = 20

class Rock(GameEntity):
    def __init__(self, world, image):
        GameEntity.__init__(self, world, "rock", image)

class Ant(GameEntity):

    def __init__(self, world, image):

        GameEntity.__init__(self, world, "ant", image)

        exploring_state = AntStateExploring(self)
        seeking_state = AntStateSeeking(self)
        delivering_state = AntStateDelivering(self)

        self.brain.add_state(exploring_state)
        self.brain.add_state(seeking_state)
        self.brain.add_state(delivering_state)
        self.carry_image = None
        self.carry_leaf = None

    def carry(self, image, leaf):

        self.carry_image = image
        self.carry_leaf = leaf

    def drop(self, surface):

        if self.carry_image:
            x, y = self.location
            w, h = self.carry_image.get_size()
            surface.blit(self.carry_image, (x-w, y-h/2))
            # self.world.remove_entity(self.carry_leaf)
            self.carry_image = None
            self.carry_leaf = None

    def render(self, surface):

        GameEntity.render(self, surface)

        if self.carry_image:
            x, y = self.location
            w, h = self.carry_image.get_size()
            surface.blit(self.carry_image, (x-w, y-h/2))

class AntStateExploring(State):

    def __init__(self, ant):

        State.__init__(self, "exploring")
        self.ant = ant

    def random_destination(self):

        w, h = SCREEN_SIZE
        dest = Vector2(randint(0, w), randint(0, h))
        self.ant.destination = dest

    def do_actions(self):
        self.random_destination()

    def check_conditions(self):
        rock = self.ant.world.get_close_entity("rock", self.ant.location)
        if self.ant.world.in_obstacle(self.ant.location):
            return "exploring"

        leaf = self.ant.world.get_close_entity("leaf", self.ant.location)
        if leaf is not None:
            self.ant.leaf_id = leaf.id
            return "seeking"


        return None

    def entry_actions(self):

        self.ant.speed = 120.
        self.random_destination()


class AntStateSeeking(State):

    def __init__(self, ant):

        State.__init__(self, "seeking")
        self.ant = ant
        self.leaf_id = None

    def check_conditions(self):

        leaf = self.ant.world.get(self.ant.leaf_id)
        if leaf is None:
            return "exploring"

        if self.ant.location.get_distance_to(leaf.location) < 1.0:
            self.ant.carry(leaf.image, leaf)
            leaf.stock -= 10
            if leaf.stock <= 0:
                self.ant.world.remove_entity(leaf)
            return "delivering"


        return None

    def entry_actions(self):

        leaf = self.ant.world.get(self.ant.leaf_id)
        if leaf is not None:
            self.ant.destination = leaf.location
            self.ant.speed = 160. + randint(-20, 20)


class AntStateDelivering(State):

    def __init__(self, ant):

        State.__init__(self, "delivering")
        self.ant = ant


    def check_conditions(self):

        if Vector2(*NEST_POSITION).get_distance_to(self.ant.location) < NEST_SIZE:
            if (randint(1, 10) == 1):
                self.ant.drop(self.ant.world.background)
                return "exploring"

        return None

    def random_destination(self):

        w, h = SCREEN_SIZE
        dest = Vector2(randint(0, w), randint(0, h))
        self.ant.destination = dest

    def do_actions(self):
        self.random_destination()
    def entry_actions(self):

        self.ant.speed = 60.
        random_offset = Vector2(randint(-20, 20), randint(-20, 20))
        # self.ant.destination = Vector2(*NEST_POSITION) + random_offset
        self.random_destination()

class GameOptions:
    SCREEN_SIZE = (600, 600)
    NEST_POSITION = (SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2)
    AGENT_COUNT = 10
    ROCK_COUNT = 20
    NEST_SIZE = 40.
    LEAF_COUNT = 20

def run(options):

    if options:
        SCREEN_SIZE = options.SCREEN_SIZE
        AGENT_COUNT = options.AGENT_COUNT
        ROCK_COUNT = options.ROCK_COUNT
        LEAF_COUNT = options.LEAF_COUNT

    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE, 0, 32)

    world = World()

    w, h = SCREEN_SIZE

    clock = pygame.time.Clock()

    ant_image = pygame.image.load("ant.png").convert_alpha()
    leaf_image = pygame.image.load("leaf.png").convert_alpha()
    leaf_image2 = pygame.image.load("leaf2.png").convert_alpha()
    leaf_image3 = pygame.image.load("leaf3.png").convert_alpha()
    rock_image = pygame.image.load("rock.png").convert_alpha()

    for ant_no in xrange(AGENT_COUNT):
        ant = Ant(world, ant_image)
        ant.location = Vector2(NEST_POSITION[0], NEST_POSITION[1])
        ant.brain.set_state("exploring")
        world.add_entity(ant)

    for rock_no in xrange(ROCK_COUNT):
        rock = Rock(world, rock_image)
        x_pos = randint(0, w)
        y_pos = randint(0, h)
        pos = (x_pos, y_pos)
        while world.is_inside_nest(pos):
            x_pos = randint(0, w)
            y_pos = randint(0, h)
        rock.location = Vector2(x_pos, y_pos)
        world.add_entity(rock)

    for min_no in xrange(LEAF_COUNT):
        random_leaf = randint(0, 2)
        if random_leaf == 0:
            leaf = Leaf(world, leaf_image)
        elif random_leaf == 1:
            leaf = Leaf(world, leaf_image2)
        else:
            leaf = Leaf(world, leaf_image3)
        loc = (randint(0, w), randint(0, h))
        while world.is_inside_nest(loc):
            loc = (randint(0, w), randint(0, h))
        leaf.location = Vector2(*loc)
        world.add_entity(leaf)

    while True:

        for event in pygame.event.get():
            if event.type == QUIT:
                return

        time_passed = clock.tick(30)


        world.process(time_passed)
        world.render(screen)

        pygame.display.update()
