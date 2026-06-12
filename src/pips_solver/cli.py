#!/usr/bin/env python3
"""CLI tool to solve pips puzzles from JSON files."""

import sys
import json
import time
from pathlib import Path
from pips_solver.pips_solver import DominoSuperSolver


def load_board(board_file: Path):
    """Load and parse board JSON from disk."""
    with board_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def solve_board(board: dict) -> dict:
    """Solve a board payload and return a serializable result object."""
    solver = DominoSuperSolver(board)
    solved = solver.solve()
    if solved:
        return {
            "status": "solved",
            "solution": solver.get_solution_dict(),
            "solution_steps": solver.solution_steps,
            "search_stats": solver.get_search_stats(),
            "tested_dominoes_order": solver.get_tested_dominoes_order(),
        }
    return {
        "status": "no_solution",
        "search_stats": solver.get_search_stats(),
        "tested_dominoes_order": solver.get_tested_dominoes_order(),
    }


def solve_board_details(board: dict):
    """Solve board and return serializable result plus raw solution details."""
    solver = DominoSuperSolver(board)
    solved = solver.solve()
    if solved:
        result = {
            "status": "solved",
            "solution": solver.get_solution_dict(),
            "solution_steps": solver.solution_steps,
            "search_stats": solver.get_search_stats(),
            "tested_dominoes_order": solver.get_tested_dominoes_order(),
        }
        return result, solver.board, solver.solution_board
    return {
        "status": "no_solution",
        "search_stats": solver.get_search_stats(),
        "tested_dominoes_order": solver.get_tested_dominoes_order(),
    }, None, None


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

    value_map = {}
    for key, value in solution.items():
        row, col = eval(key)  # Parse tuple string like "(0, 1)"
        value_map[(row, col)] = str(value)

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
            value = grid[row][col] if row < len(grid) and col < len(grid[row]) else 0
            row_values.append("" if value <= 0 else str(value))
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
        if raw_solution is None:
            raise RuntimeError("Expected solved result to include raw solution data")
        print_solution_to_console(result.get("solution", {}), grid, board["selected"])
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
