import React, { useState, useEffect } from "react";

type ShapeType = "circle" | "rectangle";

interface Shape {
  id: number;
  shapeType: ShapeType;
  radius?: number;
  width?: number;
  height?: number;
  angle: number;
  position: [number, number];
  color: number;
}

function App() {
  const [shapes, setShapes] = useState<Shape[]>([]);
  const [shapeType, setShapeType] = useState<ShapeType>("circle");
  const [radius, setRadius] = useState<number>(10);
  const [width, setWidth] = useState<number>(30);
  const [height, setHeight] = useState<number>(30);
  const [angle, setAngle] = useState<number>(0);
  const [color, setColor] = useState<number>(0);
  const [removeMode, setRemoveMode] = useState<boolean>(false);
  const [puzzleType, setPuzzleType] = useState<string>("PHYRE");
  const [puzzles, setPuzzles] = useState<any[]>([]);
  const [selectedPuzzle, setSelectedPuzzle] = useState<string>("");

  // Fetch puzzle list from the backend by puzzleType
  useEffect(() => {
    fetch(`/puzzles?puzzle_type=${puzzleType}`)
      .then((res) => res.json())
      .then((data) => {
        setPuzzles(data);
        setSelectedPuzzle("");
      })
      .catch(console.error);
  }, [puzzleType]);

  function handleCanvasClick(e: React.MouseEvent<HTMLDivElement>) {
    if (removeMode) {
      // removing shapes by finding nearest shape, for example
      // or you can record the bounding boxes
      // simpler approach: do nothing for now
      return;
    }
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setShapes((prev) => [
      ...prev,
      {
        id: Math.random(),
        shapeType,
        radius,
        width,
        height,
        angle,
        position: [x, y],
        color,
      },
    ]);
  }

  function handleRemoveModeToggle() {
    setRemoveMode(!removeMode);
  }

  function handleShapeRemove(id: number) {
    setShapes(shapes.filter((s) => s.id !== id));
  }

  function simulateNewPuzzle() {
    // We'll just do a local simulation or call the backend with a "preview" style
    // but let's keep it simple for now:
    alert("Simulate pressed - call backend if needed for real-time preview.");
  }

  function resetShapes() {
    setShapes([]);
  }

  async function addToTestSet() {
    const payload = {
      shapes: shapes.map((s) => ({
        shapeType: s.shapeType,
        radius: s.radius,
        width: s.width,
        height: s.height,
        angle: s.angle,
        position: s.position,
        color: s.color,
      })),
    };
    const res = await fetch("/puzzles/create_test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    console.log(data);
    alert(`Created puzzle with id: ${data.puzzle_id}`);
  }

  async function addPhyrePuzzleToTestSet(pid: string) {
    // calls /puzzles/{puzzle_id}/add_to_test
    const res = await fetch(`/puzzles/${pid}/add_to_test`, { method: "POST" });
    const data = await res.json();
    alert(`Puzzle ${data.puzzle_id} added to test set`);
  }

  async function simulateSelectedPuzzle() {
    if (!selectedPuzzle) {
      alert("Select a puzzle from the dropdown first!");
      return;
    }
    const res = await fetch(`/simulate/${selectedPuzzle}`, { method: "POST" });
    const data = await res.json();
    alert(
      `Puzzle ${data.puzzle_id} simulation completed. Goal reached? ${data.goal_reached}`
    );
  }

  return (
    <div style={{ display: "flex", gap: "1rem", padding: "1rem" }}>
      {/* Left Controls */}
      <div style={{ width: "250px" }}>
        <h3>Shape Toolbar</h3>
        <label>Shape Type: </label>
        <select
          value={shapeType}
          onChange={(e) => setShapeType(e.target.value as ShapeType)}
        >
          <option value="circle">Circle</option>
          <option value="rectangle">Rectangle</option>
        </select>
        {shapeType === "circle" && (
          <>
            <label>Radius: </label>
            <input
              type="number"
              value={radius}
              onChange={(e) => setRadius(parseFloat(e.target.value))}
            />
          </>
        )}
        {shapeType === "rectangle" && (
          <>
            <label>Width: </label>
            <input
              type="number"
              value={width}
              onChange={(e) => setWidth(parseFloat(e.target.value))}
            />
            <label>Height: </label>
            <input
              type="number"
              value={height}
              onChange={(e) => setHeight(parseFloat(e.target.value))}
            />
          </>
        )}
        <br />
        <label>Angle: </label>
        <input
          type="number"
          value={angle}
          onChange={(e) => setAngle(parseFloat(e.target.value))}
        />
        <br />
        <label>Color (int): </label>
        <input
          type="number"
          value={color}
          onChange={(e) => setColor(parseInt(e.target.value))}
        />
        <br />
        <button onClick={handleRemoveModeToggle}>
          {removeMode ? "Exit Remove Mode" : "Remove Mode"}
        </button>
        <hr />
        <button onClick={simulateNewPuzzle}>Simulate (Preview)</button>
        <button onClick={resetShapes}>Reset</button>
        <button onClick={addToTestSet}>Add to Test Set</button>
      </div>

      {/* Canvas / Objects */}
      <div
        style={{
          width: "400px",
          height: "400px",
          border: "1px solid black",
          position: "relative",
        }}
        onClick={handleCanvasClick}
      >
        {shapes.map((s) => {
          if (s.shapeType === "circle") {
            return (
              <div
                key={s.id}
                onClick={() => removeMode && handleShapeRemove(s.id)}
                style={{
                  position: "absolute",
                  left: s.position[0] - (s.radius || 0),
                  top: s.position[1] - (s.radius || 0),
                  width: (s.radius || 10) * 2,
                  height: (s.radius || 10) * 2,
                  borderRadius: "50%",
                  backgroundColor: "#CCC",
                  transform: `rotate(${s.angle}deg)`,
                  cursor: removeMode ? "pointer" : "default",
                }}
              ></div>
            );
          } else {
            return (
              <div
                key={s.id}
                onClick={() => removeMode && handleShapeRemove(s.id)}
                style={{
                  position: "absolute",
                  left: s.position[0] - (s.width || 0) / 2,
                  top: s.position[1] - (s.height || 0) / 2,
                  width: s.width,
                  height: s.height,
                  backgroundColor: "#CCC",
                  transform: `rotate(${s.angle}deg)`,
                  cursor: removeMode ? "pointer" : "default",
                }}
              ></div>
            );
          }
        })}
      </div>

      {/* Right side: Toggle puzzle type, list puzzles, pick puzzle, simulate */}
      <div style={{ width: "300px" }}>
        <h3>Existing Puzzles</h3>
        <label>Choose puzzle type: </label>
        <select
          value={puzzleType}
          onChange={(e) => setPuzzleType(e.target.value)}
        >
          <option value="PHYRE">PHYRE</option>
          <option value="TEST">TEST</option>
        </select>
        <br />
        <label>Puzzles: </label>
        <select
          value={selectedPuzzle}
          onChange={(e) => setSelectedPuzzle(e.target.value)}
        >
          <option value="">--Select Puzzle--</option>
          {puzzles.map((p) => (
            <option key={p.puzzle_id} value={p.puzzle_id}>
              {p.puzzle_id}
            </option>
          ))}
        </select>
        <div>
          <button onClick={simulateSelectedPuzzle}>Simulate Puzzle</button>
          {puzzleType === "PHYRE" && selectedPuzzle && (
            <button onClick={() => addPhyrePuzzleToTestSet(selectedPuzzle)}>
              Add This PHYRE Puzzle to Test Set
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
