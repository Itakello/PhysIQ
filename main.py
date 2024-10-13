import json
import sys
from pathlib import Path
from typing import Any

import pygame
import pymunk
import pymunk.pygame_util

from src.config import config
from src.shapes.base_shape import BaseShape
from src.shapes.circle import Circle
from src.shapes.polygon import Polygon
from src.shapes.rectangle import Rectangle


def create_shape(shape_data: dict, height: int) -> BaseShape:
    color = config.COLORS[shape_data["color"]]
    # Flip y-coordinate
    position = (shape_data["position"][0], height - shape_data["position"][1])

    if shape_data["shapeType"] == 1:  # Circle
        shape = Circle(
            color=color,
            position=position,
            body_type=shape_data["bodyType"],
            diameter=shape_data["diameter"],
        )
    elif shape_data["shapeType"] == 0:  # Polygon
        shape = Polygon(
            color=color,
            position=position,
            body_type=shape_data["bodyType"],
            vertices=shape_data["vertices"],
            angle=-shape_data["angle"],
        )
    elif shape_data["shapeType"] == 2:  # Rectangle
        vertices = shape_data["vertices"]
        width = abs(vertices[0][0] - vertices[2][0])
        height = abs(vertices[0][1] - vertices[2][1])
        shape = Rectangle(
            color=color,
            position=position,
            body_type=shape_data["bodyType"],
            width=width,
            height=height,
            angle=-shape_data["angle"],
        )
    else:
        raise ValueError(f"Unsupported shape type: {shape_data['shapeType']}")

    shape.body.angular_damping = config.DEFAULT_ANGULAR_DAMPING
    shape.body.linear_damping = config.DEFAULT_LINEAR_DAMPING

    return shape


def run_simulation(config_data: dict, config_filename: str) -> None:
    pygame.init()
    screen = pygame.display.set_mode(
        [dim * config.SCALE_FACTOR for dim in config_data["scene_dimensions"]]
    )
    pygame.display.set_caption(f"Pymunk Simulation - {config_filename}")
    clock = pygame.time.Clock()

    space = pymunk.Space()
    space.gravity = (0, config.DEFAULT_GRAVITY)  # Pymunk uses positive y-axis downwards
    space.iterations = 10  # Increase solver iterations

    draw_options = pymunk.pygame_util.DrawOptions(screen)
    draw_options.transform = pymunk.Transform.scaling(config.SCALE_FACTOR)

    height = config_data["scene_dimensions"][1]
    shapes = [create_shape(body, height) for body in config_data["bodies"]]
    for shape in shapes:
        shape.add_to_space(space)

    fixed_time_step = 1.0 / config.FPS
    scaled_time_step = fixed_time_step * config.TIME_SCALE
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((255, 255, 255))

        for _ in range(config.SIMULATION_STEPS_PER_FRAME):
            space.step(scaled_time_step)

        space.debug_draw(draw_options)

        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r") as f:
        config_data = json.load(f)
    return config_data


def main(config_filename: str) -> None:
    config_path = Path("task_jsons") / config_filename
    config_data = load_config(config_path)
    run_simulation(config_data, config_filename)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <config_filename>")
        sys.exit(1)
    main(sys.argv[1])
