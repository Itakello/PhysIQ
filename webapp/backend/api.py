# File: /PhysIQ/webapp/backend/api.py

from typing import Any

import uvicorn
from dask.distributed import Client, as_completed
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.managers.db_manager import MongoDBManager
from src.utils.box2d_runner import run_simulation
from src.utils.db_schemas import PuzzleSchema

app = FastAPI(title="PhysIQ API")
dask_client = Client()  # Connects to local Dask cluster by default

# Minimal DB Manager setup
db_manager = MongoDBManager(db_name="physiq_db")


class NewShape(BaseModel):
    shapeType: str  # "circle" or "rectangle"
    radius: float | None
    width: float | None
    height: float | None
    angle: float
    position: list[float]  # x,y
    color: int


class NewPuzzleRequest(BaseModel):
    # Optionally you can store metadata like 'test_condition' or 'description' if you like
    shapes: list[NewShape]
    # etc...


@app.get("/puzzles/")
def list_puzzles_by_type(puzzle_type: str = None) -> list[dict]:
    """
    Return a list of puzzle documents. If puzzle_type is provided, filter by that type.
    """
    query = {}
    if puzzle_type:
        query["puzzle_type"] = puzzle_type
    puzzles = list(db_manager.db["puzzles"].find(query))
    # Convert ObjectId to string for JSON serialization
    for p in puzzles:
        p["_id"] = str(p["_id"])
    return puzzles


@app.post("/puzzles/{puzzle_id}/add_to_test")
def add_puzzle_to_test_set(puzzle_id: str) -> dict[str, str]:
    """
    Flag an existing puzzle (e.g. of type PHYRE) as also belonging to the test set.
    We'll just store an extra field 'in_test_set=True'.
    """
    puzzles_coll = db_manager.db["puzzles"]
    puzzle = puzzles_coll.find_one({"puzzle_id": puzzle_id})
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")

    # Mark it in the DB
    puzzles_coll.update_one({"puzzle_id": puzzle_id}, {"$set": {"in_test_set": True}})
    return {
        "status": "ok",
        "puzzle_id": puzzle_id,
        "message": "Puzzle added to test set",
    }


@app.post("/puzzles/create_test")
def create_test_puzzle(payload: NewPuzzleRequest) -> dict[str, Any]:
    """
    Create a brand-new puzzle with puzzle_type="TEST" from shapes passed in from the React front-end.
    """
    from src.utils.db_schemas import (
        BodyData,
        MetadataData,
        PuzzleSchema,
        RelationshipData,
    )

    # Build a minimal puzzle dictionary
    # For now, let's assume no "relationship" is needed or you can define a default
    # Adjust as you see fit
    puzzle_doc = {
        "puzzle_id": "test_custom_...",  # Possibly generate an ID or unique name
        "puzzle_type": "TEST",
        "bodies": [],
        "relationship": {"bodyId1": 0, "bodyId2": 1, "relationships": []},
        "metadata": {"description": "Custom test puzzle", "tier": "CUSTOM"},
    }

    for idx, shape in enumerate(payload.shapes):
        if shape.shapeType == "circle":
            body_dict = {
                "position": shape.position,
                "body_type": 1,  # dynamic by default
                "color": shape.color,
                "shape_type": 1,  # circle
                "angle": shape.angle,
                "radius": shape.radius,
            }
        elif shape.shapeType == "rectangle":
            # approximate a rectangle with polygon vertices or set shape_type=0 with vertices
            w, h = shape.width, shape.height
            # center-based
            x, y = shape.position
            angle = shape.angle
            # define rectangle corners
            vertices = [
                [x - w / 2, y - h / 2],
                [x + w / 2, y - h / 2],
                [x + w / 2, y + h / 2],
                [x - w / 2, y + h / 2],
            ]
            body_dict = {
                "position": [0, 0],  # We'll store actual position in vertices
                "body_type": 1,  # dynamic
                "color": shape.color,
                "shape_type": 0,  # polygon
                "angle": angle,
                "vertices": vertices,
            }
        else:
            continue

        puzzle_doc["bodies"].append(body_dict)

    # Pydantic validation
    puzzle_schema = PuzzleSchema(**puzzle_doc)
    db_manager.insert_puzzle(puzzle_schema)

    return {"status": "created", "puzzle_id": puzzle_doc["puzzle_id"]}


@app.post("/simulate/{puzzle_id}")
def simulate_puzzle(puzzle_id: str):
    """
    Simulate a single puzzle from the DB. Return whether the goal was reached (if relevant).
    """
    puzzle = db_manager.db["puzzles"].find_one({"puzzle_id": puzzle_id})
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")

    # Run in a Dask future to avoid blocking
    future = dask_client.submit(run_simulation, puzzle)
    result = future.result()
    is_goal_reached, _img = result
    return {"puzzle_id": puzzle_id, "goal_reached": is_goal_reached}


@app.post("/simulate/batch")
def simulate_batch(params: dict[str, list[float]]):
    """
    Example: we can define a request body that says:
      {
        "puzzle_ids": ["test_custom_1", "test_custom_2"],
        "gravities": [100, 200, 300],
        ...
      }
    Then we run them in parallel with each combination or something like that.
    Adjust to your needs.
    """
    puzzle_ids = params.get("puzzle_ids", [])
    gravities = params.get("gravities", [])
    if not puzzle_ids or not gravities:
        return {"error": "missing fields puzzle_ids or gravities"}

    futures = []
    for pid in puzzle_ids:
        puzzle_doc = db_manager.db["puzzles"].find_one({"puzzle_id": pid})
        if not puzzle_doc:
            continue
        for g in gravities:
            # Provide a wrapper function so we can override gravity
            def sim_with_gravity(puz, gravity):
                from Box2D import b2World

                # Slight hack: we temporarily override default gravity in run_simulation
                # Or create a new specialized function that sets gravity.
                # For brevity:
                return run_simulation(puz)

            futures.append(dask_client.submit(sim_with_gravity, puzzle_doc, g))

    results = []
    for fut in as_completed(futures):
        res = fut.result()
        results.append(res)

    return {"results": results}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
