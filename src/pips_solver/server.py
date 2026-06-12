"""
Web server for pips solver frontend.
Serves the static frontend and provides a solve API endpoint.
"""

from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path
import json
import time
from .pips_solver import DominoSuperSolver

app = Flask(__name__, static_folder=None)

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


def run(host="127.0.0.1", port=8000, debug=False):
    """Run the Flask development server."""
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run(debug=True)
