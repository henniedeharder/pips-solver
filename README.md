# Pips Solver

A dominoes puzzle solver with a visual board builder frontend.

## Frontend Board Builder

A static frontend to define pips puzzles with area constraints.

### Features

- Drag across squares in edit mode to select or unselect them.
- Change rows and columns, then rebuild the board.
- Press `Show Selected Board` to reveal selected squares as white cells with outlines.
- Press `Back To Edit` to return to selection mode.
- In selected board view, click or drag selected cells to draft an area and apply compact rule buttons (`=`, `!=`, `>`, `<`, `+`).
- For `>`, `<`, and `+` rules, the UI prompts for a number when creating the area.
- Areas are shown with a shared light color and small rule marker in the corner (for example `=`, `>5`, `4`).
- Select dominoes to use from a full 0-0 to 6-6 domino palette (organized in 7 columns).
- Press `Ready to play!` to view the final board and auto-download a JSON configuration file.

### Run Frontend

From the project root:

```bash
poetry run pips-server
```

Then open: `http://localhost:8000/`

When you press "Ready to play!", a `pips-board-*.json` file is automatically downloaded with the board configuration.

In play mode, you can press "Solve Puzzle" to solve the puzzle using the backend solver. The solution will be displayed on the board with domino numbers.

## Publish Online (GitHub Pages + Render)

This app has a static frontend and a Python API backend.

- Frontend: publish `frontend/` on GitHub Pages
- Backend: host API on Render

### 1. Backend (Render)

This repo includes `render.yaml` for one-click setup.

1. Push your repo to GitHub.
2. In Render, create a new Blueprint and select this repo.
3. Render will read `render.yaml` and create `pips-solver-api`.
4. After deploy, copy your backend URL, for example:
    `https://pips-solver-api.onrender.com`

Set CORS for your GitHub Pages domain by updating env var in Render:

- `PIPS_CORS_ORIGINS=https://YOUR_USERNAME.github.io`

If your repo is a project site (`https://YOUR_USERNAME.github.io/REPO_NAME`), the origin is still:

- `https://YOUR_USERNAME.github.io`

### 2. Frontend API URL

Edit `frontend/config.js` and set:

```js
window.PIPS_API_BASE_URL = "https://pips-solver-api.onrender.com";
```

Commit this change before deploying Pages.

### 3. Frontend (GitHub Pages)

This repo includes a workflow:

- `.github/workflows/deploy-pages.yml`

To enable GitHub Pages:

1. Go to GitHub repo Settings -> Pages.
2. Under Source, choose **GitHub Actions**.
3. Push to `main` (or run workflow manually).
4. Open your Pages URL once deployment completes.

### 4. Verify

1. Open your GitHub Pages site.
2. Build a puzzle and press "Ready to play!".
3. Confirm solve works and no CORS/network errors appear in browser devtools.

### Notes

- Free Render instances may sleep; first request can take a short while.
- For local development, leave `window.PIPS_API_BASE_URL = ""` in `frontend/config.js` and run:

```bash
poetry run pips-server
```

## Solver

A constraint-satisfaction solver that reads the JSON board configuration and finds a valid domino placement.

### Install

Install the package with poetry:

```bash
poetry install
```

### Solve a Puzzle

```bash
poetry run pips-solve <board.json> [output.json]
```

Example:
```bash
poetry run pips-solve pips-board-1234567890.json solution.json
```

When a puzzle is solved, the CLI now also prints solved cell values and a domino layout grid directly in the terminal.

The solver outputs a JSON file with the solution or a status message if no solution exists.

### Run All Sample Games

If you saved sample boards in `game-samples/`, run:

```bash
poetry run python -m pips_solver.sample_runner
```

Or, after installing scripts with `poetry install`:

```bash
poetry run pips-solve-samples
```

To print solved values for each solved sample board:

```bash
poetry run python -m pips_solver.sample_runner --show-solution
```

Results are written to `game-samples/results/` as `*.solution.json`, with a summary printed in the terminal.

### Usage in Code

```python
from pips_solver import PipsSolver
import json

with open("board.json") as f:
    board = json.load(f)

solver = PipsSolver(board)
solution = solver.solve()
if solution:
    print("Solution found!", solution)
else:
    print("No solution found.")
```
