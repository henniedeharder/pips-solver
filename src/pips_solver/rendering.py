"""Helpers for rendering and serializing solved boards."""

from __future__ import annotations

from problem import PipsProblem


def _ordered_selected_cells(problem: PipsProblem) -> list[tuple[int, int]]:
    return sorted((tuple(cell) for cell in problem.board["selected"]), key=lambda rc: (rc[0], rc[1]))


def build_solution_dict(problem: PipsProblem, values: list[int]) -> dict[str, int]:
    """Build the canonical cell->value mapping used by the API and CLI."""
    return {
        str(cell): values[index]
        for index, cell in enumerate(_ordered_selected_cells(problem))
    }


def build_solution_grid(problem: PipsProblem, values: list[int]) -> list[list[int]]:
    """Build a full board grid with -1 for non-selected cells."""
    rows = problem.board["rows"]
    cols = problem.board["cols"]
    grid = [[-1 for _ in range(cols)] for _ in range(rows)]
    for index, (row, col) in enumerate(_ordered_selected_cells(problem)):
        grid[row][col] = values[index]
    return grid


def print_selected_values(problem: PipsProblem, values: list[int]) -> None:
    """Print only the solved values in their board positions."""
    rows = problem.board["rows"]
    cols = problem.board["cols"]
    selected = set(_ordered_selected_cells(problem))
    value_by_cell = {
        cell: values[index]
        for index, cell in enumerate(_ordered_selected_cells(problem))
    }

    print("\nSolved Value Board:")
    for row in range(rows):
        line_cells = []
        for col in range(cols):
            if (row, col) in selected:
                line_cells.append(f"{value_by_cell[(row, col)]:>2}")
            else:
                line_cells.append("  ")
        print("  ".join(line_cells).rstrip())