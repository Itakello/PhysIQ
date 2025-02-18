"""

Helper classes and functions to build Box2D bodies/fixtures based on
puzzle data that originally came from the DB or from the PhyRE tasks.

We define multiple shape creators (Circle, Polygon, Compound) and a single
public function 'create_pybox2d_body' that dispatches to the correct shape creation.
"""

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

from ..utils.const import (
    DEFAULT_DENSITY,
    DEFAULT_ELASTICITY,
    DEFAULT_FRICTION,
    SCENE_DIMENSIONS,
)


def _get_body_type(body_type: int) -> Any:
    """
    Map puzzle bodyType (0=static,1=dynamic, maybe 2=kinematic if your data includes that)
    to Box2D's b2BodyType. Adjust as needed for your data conventions.
    """
    if body_type == 0:
        return b2_staticBody
    elif body_type == 1:
        return b2_dynamicBody
    else:
        # fallback for unusual or 2 => kinematic
        return b2_kinematicBody


def _set_default_fixture_properties(fix_def: b2FixtureDef) -> None:
    """Set common fixture properties from defaults."""
    fix_def.density = DEFAULT_DENSITY
    fix_def.friction = DEFAULT_FRICTION
    fix_def.restitution = DEFAULT_ELASTICITY


def _create_circle_fixture(radius: float) -> b2FixtureDef:
    """
    Create a circle fixture definition from puzzle data.
    puzzle data example: {
       "radius": <float>,
       "color": <int>,
       "angle": <float>,
       "friction": <float>, etc...
    }
    We'll rely on puzzle data to define friction, restitution, density, etc. if needed.
    """
    circle_shape = b2CircleShape(radius=radius)
    fix_def = b2FixtureDef()
    fix_def.shape = circle_shape
    _set_default_fixture_properties(fix_def)
    return fix_def


def _create_polygon_fixture(vertices: list[list[float]]) -> b2FixtureDef:
    """
    Create a polygon fixture definition from puzzle data.
    """
    polygon_shape = b2PolygonShape(vertices=vertices)
    fix_def = b2FixtureDef()
    fix_def.shape = polygon_shape
    _set_default_fixture_properties(fix_def)
    return fix_def


def _create_compound_fixtures(shapes: list[Any]) -> list[b2FixtureDef]:
    """
    Creates multiple fixtures (one for each polygon in shapes_data).
    The puzzle data might look like:
    {
      "shapes": [
         {"type": "polygon", "vertices": [...], ... },
         {"type": "polygon", "vertices": [...], ... },
         ...
      ],
      ...
    }
    """
    fix_defs = []
    for shp in shapes:
        # We assume these are polygons:
        polygon_shape = b2PolygonShape(vertices=shp["vertices"])
        fix_def = b2FixtureDef(shape=polygon_shape)
        _set_default_fixture_properties(fix_def)
        fix_defs.append(fix_def)

    return fix_defs


def create_pybox2d_body(
    world, body_data: dict, body_index: int, is_target: bool = False
):  # -> Any:
    """
    Create a single Box2D body + fixture(s) in the given Box2D world.

    body_data (dict) typical fields:
       - position: [x, y]
       - bodyType: int
       - angle: float (radians)
       - shapeType: int  (0=polygon,1=circle,2=polygon,3=compound,...)
       - vertices, radius, shapes, etc. (depending on shapeType)
       - friction, density, elasticity, etc. (optional)
    body_index: integer ID to store in fixture.userData so we can identify collisions
    is_target:  whether this body is one of the bodies we want to check collision for

    Returns the created b2Body.
    """
    # 1) BodyDef
    body_def = b2BodyDef()
    body_def.type = _get_body_type(body_data["body_type"])
    px, py = body_data["position"]
    body_def.position = b2Vec2(px, py)
    # Note: Box2D expects radians for angles
    angle = body_data.get("angle", 0.0)
    body_def.angle = angle

    # 2) Create the body
    body = world.CreateBody(body_def)

    # 3) Create fixture(s) depending on shapeType
    st = body_data["shape_type"]
    if st in [1]:  # circle
        fix_def = _create_circle_fixture(body_data["radius"])
        # For collision detection, store in fixture.userData
        fix_def.userData = {
            "body_id": body_index,
            "target": is_target,
        }
        body.CreateFixture(fix_def)
    elif st in [0, 2]:  # polygon
        fix_def = _create_polygon_fixture(body_data["vertices"])
        fix_def.userData = {
            "body_id": body_index,
            "target": is_target,
        }
        body.CreateFixture(fix_def)
    elif st in [3, 4]:  # compound
        fixture_defs = _create_compound_fixtures(body_data["shapes"])
        for fd in fixture_defs:
            fd.userData = {
                "body_id": body_index,
                "target": is_target,
            }
            body.CreateFixture(fd)
    else:
        # If shapeType is unknown, do nothing or raise an error
        pass

    return body
