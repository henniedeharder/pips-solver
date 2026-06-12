#!/usr/bin/env python3
"""Batch runner for solving sample pips boards."""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path

from pips_solver.pips_solver import DominoSuperSolver


def print_result_value_board(solution: dict, selected: list[list[int]]) -> None:
    """Print solved values as a row/column board."""
    if selected:
        min_row = min(cell[0] for cell in selected)
        max_row = max(cell[0] for cell in selected)
        min_col = min(cell[1] for cell in selected)
        max_col = max(cell[1] for cell in selected)
    else:
        parsed = [eval(key) for key in solution]
        min_row = min(row for row, _ in parsed)
        max_row = max(row for row, _ in parsed)
        min_col = min(col for _, col in parsed)
        max_col = max(col for _, col in parsed)

    value_grid = {}
    for key, value in solution.items():
        row, col = eval(key)
        value_grid[(row, col)] = str(value)

    print("Solved Value Board:")
    for row in range(min_row, max_row + 1):
        row_values = []
        for col in range(min_col, max_col + 1):
            row_values.append(value_grid.get((row, col), ""))
        line = "  ".join(f"{cell:>2}" for cell in row_values)
        print(f"  {line}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Solve all sample boards in a directory."
    )
    parser.add_argument(
        "samples_dir",
        nargs="?",
        default="game-samples",
        help="Directory containing sample board JSON files (default: game-samples)",
    )
    parser.add_argument(
        "--out-dir",
        default="game-samples/results",
        help="Directory where result JSON files are written (default: game-samples/results)",
    )
    parser.add_argument(
        "--show-solution",
        action="store_true",
        help="Print solved cell values in terminal for solved boards.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    samples_dir = Path(args.samples_dir)
    out_dir = Path(args.out_dir)

    if not samples_dir.exists() or not samples_dir.is_dir():
        print(f"Error: Samples directory '{samples_dir}' does not exist or is not a directory.")
        raise SystemExit(1)

    board_files = sorted(samples_dir.glob("pips-board-*.json"))
    if not board_files:
        print(f"No pips-board-*.json sample boards found in '{samples_dir}'.")
        raise SystemExit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    solved = 0
    no_solution = 0
    failed = 0
    total_start = time.perf_counter()

    print(f"Found {len(board_files)} sample board(s) in {samples_dir}")
    for board_file in board_files:
        output_file = out_dir / f"{board_file.stem}.solution.json"
        
        print(f"\n=== {board_file.name} ===")
        board_start = time.perf_counter()
        
        try:
            with open(board_file, 'r') as f:
                board_data = json.load(f)
            
            solver = DominoSuperSolver(board_data)
            solved_flag = solver.solve()
            board_elapsed = time.perf_counter() - board_start
            
            if solved_flag:
                result = solver.save_solution(output_file)
                status = "solved"
                solved += 1
                
                # Print the board nicely
                solver.print_solution_board(board_data.get("selected"))
                
                if args.show_solution:
                    print_result_value_board(result.get("solution", {}), board_data["selected"])
            else:
                result = solver.save_solution(output_file)
                status = "no_solution"
                no_solution += 1
            
            print(f"Status: {status}")
            print(f"Result: {output_file}")
            print(f"Solve time: {board_elapsed:.3f}s")
            print(f"Stats: {solver.stats}")
            
        except Exception as exc:
            board_elapsed = time.perf_counter() - board_start
            failed += 1
            error_file = out_dir / f"{board_file.stem}.error.json"
            with error_file.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "status": "error",
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                    f,
                    indent=2,
                )
            print(f"Status: error")
            print(f"Error: {exc}")
            print(f"Solve time: {board_elapsed:.3f}s")
            print(f"Details: {error_file}")

    print("\n--- Summary ---")
    print(f"Solved: {solved}")
    print(f"No solution: {no_solution}")
    print(f"Failed: {failed}")
    print(f"Total time: {time.perf_counter() - total_start:.3f}s")

    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()