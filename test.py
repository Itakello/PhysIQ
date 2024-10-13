import sys
import time

import pygame
import pymunk
import pymunk.pygame_util

from src.shapes.circle import Circle
from src.shapes.square import Square
from src.shapes.triangle import Triangle


def create_boundaries(space) -> None:
    static_lines = [
        pymunk.Segment(space.static_body, (0, 0), (0, 600), 5),  # Left
        pymunk.Segment(space.static_body, (0, 600), (600, 600), 5),  # Top
        pymunk.Segment(space.static_body, (600, 600), (600, 0), 5),  # Right
        pymunk.Segment(space.static_body, (600, 0), (0, 0), 5),  # Bottom
    ]
    for line in static_lines:
        line.friction = 1.0
        space.add(line)


def create_ball(space) -> pymunk.Circle:
    mass = 1
    radius = 14
    moment = pymunk.moment_for_circle(mass, 0, radius)
    body = pymunk.Body(mass, moment)
    body.position = 400, 300
    shape = pymunk.Circle(body, radius)
    space.add(body, shape)
    return shape


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Pymunk Simulation")
    clock = pygame.time.Clock()
    space = pymunk.Space()
    space.gravity = 0, 900  # Change gravity direction

    draw_options = pymunk.pygame_util.DrawOptions(screen)

    ball = create_ball(space)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((255, 255, 255))

        space.step(1 / 60.0)
        space.debug_draw(draw_options)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
