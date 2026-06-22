#!/usr/bin/env python3
"""CLI tool to solve pips puzzles from JSON files."""

import sys
import json
import time
from pathlib import Path

from .problem import PipsProblem
from .rendering import build_solution_dict, build_solution_grid, print_selected_values
from .solver_ortools import CpSatSolver


def load_board(board_file: Path):
    """Load and parse board JSON from disk."""
    with board_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def solve_board(board: dict) -> dict:
    """Solve a board payload and return a serializable result object."""
    problem = PipsProblem(board)
    solver = CpSatSolver(problem)
    start = time.perf_counter()
    solutions = solver.solve()
    elapsed = time.perf_counter() - start

    if solutions:
        values = solutions[0].vals
        return {
            "status": "solved",
            "solution": build_solution_dict(problem, values),
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
        }
    return {
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
    }


def solve_board_details(board: dict):
    """Solve board and return serializable result plus raw solution details."""
    problem = PipsProblem(board)
    solver = CpSatSolver(problem)
    start = time.perf_counter()
    solutions = solver.solve()
    elapsed = time.perf_counter() - start

    if solutions:
        values = solutions[0].vals
        result = {
            "status": "solved",
            "solution": build_solution_dict(problem, values),
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
        }
        return result, problem, values

    result = {
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
    }
    return result, problem, None


def solve_board_file(board_file: Path, output_file: Path) -> dict:
    """Solve one board file and persist result JSON."""
    board = load_board(board_file)
    result = solve_board(board)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: pips-solve <board.json> [output.json]")
        print("\nSolves a pips puzzle from a JSON board file.")
        print("Output file defaults to 'solution.json' if not specified.")
        sys.exit(1)

    board_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("solution.json")

    if not board_file.exists():
        print(f"Error: Board file '{board_file}' not found.")
        sys.exit(1)

    try:
        board = load_board(board_file)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{board_file}': {e}")
        sys.exit(1)

    print(f"Loading puzzle from {board_file}...")
    print(f"Board size: {board['rows']} x {board['cols']}")
    print(f"Selected cells: {len(board['selected'])}")
    print(f"Areas: {len(board['areas'])}")
    print(f"Dominoes: {len(board['dominoes'])}")

    print("\nSolving puzzle...")
    start = time.perf_counter()
    result, problem, values = solve_board_details(board)
    elapsed = time.perf_counter() - start

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    if result["status"] == "solved":
        print("Solution found!")
        if values is None:
            raise RuntimeError("Expected solved result to include solution values")
        print_selected_values(problem, values)
        stats = result.get("search_stats", {})
        print(
            "Search stats: "
            f"nodes={stats.get('nodes', 0)}, "
            f"backtracks={stats.get('backtracks', 0)}"
        )
        print(f"Solve time: {elapsed:.3f}s")
        print(f"Solution saved to {output_file}")
    else:
        print("No solution found.")
        stats = result.get("search_stats", {})
        print(
            "Search stats: "
            f"nodes={stats.get('nodes', 0)}, "
            f"backtracks={stats.get('backtracks', 0)}"
        )
        print(f"Solve time: {elapsed:.3f}s")
        print(f"Result saved to {output_file}")


if __name__ == "__main__":
    main()
