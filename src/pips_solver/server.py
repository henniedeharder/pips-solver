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

from .pips_solver import DominoSuperSolver

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

        solver = DominoSuperSolver(board)
        solved = solver.solve()

        if solved:
            # Convert solution to serializable format
            solution_data = solver.get_solution_dict()
            return jsonify({
                "status": "solved",
                "solution": solution_data,
                "grid": solver.solution_board,
                "solution_steps": solver.solution_steps,
                "search_stats": solver.get_search_stats(),
                "tested_dominoes_order": solver.get_tested_dominoes_order(),
            })
        else:
            return jsonify({
                "status": "no_solution",
                "search_stats": solver.get_search_stats(),
                "tested_dominoes_order": solver.get_tested_dominoes_order(),
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
