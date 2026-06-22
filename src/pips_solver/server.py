"""
Web server for pips solver frontend.
Serves the static frontend and provides a solve API endpoint.
"""

import json
import os
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .problem import PipsProblem
from .rendering import build_solution_dict, build_solution_grid
from .solver_ortools import CpSatSolver

app = Flask(__name__, static_folder=None)


def _parse_cors_origins() -> list[str] | str:
    """Parse allowed CORS origins from env var.

    PIPS_CORS_ORIGINS examples:
    - "*"
    - "https://user.github.io"
    - "https://user.github.io,https://another-site.com"
    """
    raw = os.getenv("PIPS_CORS_ORIGINS", "*").strip()
    if raw == "*":
        return "*"
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or "*"


CORS(app, resources={r"/api/*": {"origins": _parse_cors_origins()}})

# Get the frontend directory path
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
SAVED_BOARDS_DIR = Path(__file__).parent.parent.parent / "saved_boards"


@app.route("/")
def index():
    """Serve the main HTML file."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    """Serve static files (CSS, JS)."""
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/solve", methods=["POST"])
def solve():
    """
    API endpoint to solve a puzzle.
    Expects JSON with board configuration.
    """
    try:
        board = request.json
        if not board:
            return jsonify({"error": "No board provided"}), 400

        problem = PipsProblem(board)
        solver = CpSatSolver(problem)
        start = time.perf_counter()
        solutions = solver.solve()
        elapsed = time.perf_counter() - start

        if solutions:
            values = solutions[0].vals
            solution_data = build_solution_dict(problem, values)
            return jsonify({
                "status": "solved",
                "solution": solution_data,
                "grid": build_solution_grid(problem, values),
                "solution_steps": [],
                "search_stats": {
                    "nodes": 0,
                    "backtracks": 0,
                    "elapsed": elapsed,
                    "nodes_visited": 0,
                    "candidate_checks": 0,
                    "placements_tried": 0,
                    "dead_ends": 0,
                    "max_depth": 0,
                },
                "tested_dominoes_order": [],
            })
        else:
            return jsonify({
                "status": "no_solution",
                "search_stats": {
                    "nodes": 0,
                    "backtracks": 0,
                    "elapsed": elapsed,
                    "nodes_visited": 0,
                    "candidate_checks": 0,
                    "placements_tried": 0,
                    "dead_ends": 0,
                    "max_depth": 0,
                },
                "tested_dominoes_order": [],
                "solution_steps": [],
            })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error",
        }), 500


@app.route("/api/save-board", methods=["POST"])
def save_board():
    """Persist a board JSON payload to disk and return the saved path."""
    try:
        board = request.json
        if not board:
            return jsonify({"error": "No board provided", "status": "error"}), 400

        SAVED_BOARDS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"pips-board-{int(time.time() * 1000)}.json"
        output_path = SAVED_BOARDS_DIR / filename

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(board, f, indent=2)

        try:
            saved_path = str(output_path.relative_to(Path.cwd()))
        except ValueError:
            saved_path = str(output_path)

        return jsonify({
            "status": "saved",
            "filename": filename,
            "path": saved_path,
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error",
        }), 500


def run(host=None, port=None, debug=False):
    """Run the Flask development server."""
    host = host or os.getenv("HOST", "127.0.0.1")
    port = int(port or os.getenv("PORT", "8000"))
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run(debug=True)
