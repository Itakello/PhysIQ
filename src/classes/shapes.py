from typing import Any

from Box2D import (
    b2_dynamicBody,
    b2_kinematicBody,
    b2_staticBody,
    b2BodyDef,
    b2CircleShape,
    b2FixtureDef,
    b2PolygonShape,
    b2Vec2,
)
from loguru import logger

from ..utils.const import DEFAULT_DENSITY, DEFAULT_ELASTICITY, DEFAULT_FRICTION

# Simple color map. Customize or expand as needed:
COLOR_MAP = {
    0: (243, 79, 70),  # red
    1: (0, 0, 0),  # black
    2: (107, 206, 187),  # green
    3: (27, 121, 242),  # azure
    4: (75, 74, 164),  # purple
    5: (185, 202, 210),  # grey
}


def _get_body_type(body_type: int) -> Any:
    if body_type == 0:
        return b2_staticBody
    elif body_type == 1:
        return b2_dynamicBody
    else:
        return b2_kinematicBody


def _set_default_fixture_properties(fix_def: b2FixtureDef) -> None:
    fix_def.density = DEFAULT_DENSITY
    fix_def.friction = DEFAULT_FRICTION
    fix_def.restitution = DEFAULT_ELASTICITY


def _create_circle_fixture(radius: float) -> b2FixtureDef:
    circle_shape = b2CircleShape(radius=radius)
    fix_def = b2FixtureDef()
    fix_def.shape = circle_shape
    _set_default_fixture_properties(fix_def)
    return fix_def


def _create_polygon_fixture(vertices: list[list[float]]) -> b2FixtureDef:
    polygon_shape = b2PolygonShape(vertices=vertices)
    fix_def = b2FixtureDef()
    fix_def.shape = polygon_shape
    _set_default_fixture_properties(fix_def)
    return fix_def


def _create_compound_fixtures(shapes: list[Any]) -> list[b2FixtureDef]:
    fix_defs = []
    for shp in shapes:
        # Assume these are polygon sub-shapes
        polygon_shape = b2PolygonShape(vertices=shp["vertices"])
        fix_def = b2FixtureDef(shape=polygon_shape)
        _set_default_fixture_properties(fix_def)
        fix_defs.append(fix_def)
    return fix_defs


def create_pybox2d_body(
    world, body_data: dict, body_index: int, is_target: bool = False
):
    """
    Create a single Box2D body + fixture(s) in the given Box2D world.
    Attach color info in fixture.userData so that PygameRenderer can fill shapes properly.
    """
    body_def = b2BodyDef()
    body_def.type = _get_body_type(body_data["body_type"])

    px, py = body_data["position"]
    body_def.position = b2Vec2(px, py)
    body_def.angle = body_data.get("angle", 0.0)

    # Create the body
    body = world.CreateBody(body_def)

    # Grab color from puzzle data (fallback to black if not found)
    color_idx = body_data.get("color", 0)
    color_rgb = COLOR_MAP.get(color_idx, (0, 0, 0))

    st = body_data["shape_type"]
    if st == 1:  # circle
        fix_def = _create_circle_fixture(body_data["radius"])
        fix_def.userData = {
            "body_id": body_index,
            "target": is_target,
            "color": color_rgb,
        }
        body.CreateFixture(fix_def)

    elif st in [0, 2]:  # polygon
        fix_def = _create_polygon_fixture(body_data["vertices"])
        fix_def.userData = {
            "body_id": body_index,
            "target": is_target,
            "color": color_rgb,
        }
        body.CreateFixture(fix_def)

    elif st in [3, 4]:  # compound (multiple polygons)
        fixture_defs = _create_compound_fixtures(body_data["shapes"])
        for fd in fixture_defs:
            fd.userData = {
                "body_id": body_index,
                "target": is_target,
                "color": color_rgb,
            }
            body.CreateFixture(fd)
    else:
        logger.warning(f"Unknown shape_type {st} encountered; skipping creation.")

    return body
