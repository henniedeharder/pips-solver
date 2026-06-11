#!/usr/bin/env python3
"""CLI tool to solve pips puzzles from JSON files."""

import sys
import json
import time
from pathlib import Path
from pips_solver.solver import PipsSolver


def load_board(board_file: Path):
    """Load and parse board JSON from disk."""
    with board_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def solve_board(board: dict) -> dict:
    """Solve a board payload and return a serializable result object."""
    solver = PipsSolver(board)
    solution = solver.solve()
    if solution:
        return {
            "status": "solved",
            "solution": {str(k): v for k, v in solution.items()},
        }
    return {"status": "no_solution"}


def solve_board_details(board: dict):
    """Solve board and return serializable result plus raw solution details."""
    solver = PipsSolver(board)
    solution = solver.solve()
    if solution:
        result = {
            "status": "solved",
            "solution": {str(k): v for k, v in solution.items()},
        }
        return result, solution, solver.get_solution_grid()
    return {"status": "no_solution"}, None, None


def print_solution_to_console(solution: dict, grid: list | None, selected: list[list[int]]) -> None:
    """Print a readable solution preview in the terminal."""
    if selected:
        min_row = min(cell[0] for cell in selected)
        max_row = max(cell[0] for cell in selected)
        min_col = min(cell[1] for cell in selected)
        max_col = max(cell[1] for cell in selected)
    else:
        rows = [row for (row, _) in solution]
        cols = [col for (_, col) in solution]
        min_row = min(rows)
        max_row = max(rows)
        min_col = min(cols)
        max_col = max(cols)

    value_map = {(row, col): str(value) for (row, col), value in solution.items()}

    print("\nSolved Value Board:")
    for row in range(min_row, max_row + 1):
        row_values = []
        for col in range(min_col, max_col + 1):
            row_values.append(value_map.get((row, col), ""))
        line = "  ".join(f"{value:>2}" for value in row_values)
        print(f"  {line}")

    if grid is None:
        return

    print("\nDomino Layout Grid:")
    for row in range(min_row, max_row + 1):
        row_values = []
        for col in range(min_col, max_col + 1):
            value = grid[row][col]
            row_values.append("" if value == 0 else str(value))
        line = "  ".join(f"{value:>2}" for value in row_values)
        print(f"  {line}")


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
    result, raw_solution, grid = solve_board_details(board)
    elapsed = time.perf_counter() - start

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    if result["status"] == "solved":
        print("Solution found!")
        print_solution_to_console(raw_solution, grid, board["selected"])
        print(f"Solve time: {elapsed:.3f}s")
        print(f"Solution saved to {output_file}")
    else:
        print("No solution found.")
        print(f"Solve time: {elapsed:.3f}s")
        print(f"Result saved to {output_file}")


if __name__ == "__main__":
    main()
