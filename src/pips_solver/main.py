"""
main.py
-------
Example usage: load a board JSON and solve with the available solvers.
"""

from __future__ import annotations

import json
import time

from problem import PipsProblem
from rendering import print_selected_values
from solver_backtrack import BacktrackSolver
from solver_ortools import CpSatSolver
from solver_smart import SmartSolver


def extract_solution_values(solution) -> list[int]:
    """Extract the value list from any solver solution representation."""
    if isinstance(solution, dict):
        return solution["vals"]
    return solution.vals


def print_solver_result(name: str, problem: PipsProblem, solutions, elapsed: float) -> None:
    print(f"\n── {name} ──────────────────────────────────────")
    print(f"Found {len(solutions)} solution(s) in {elapsed:.4f}s")
    for idx, solution in enumerate(solutions, start=1):
        values = extract_solution_values(solution)
        print(f"Solution {idx}:")
        print_selected_values(problem, values)

def run_backtrack(problem):
    solver = BacktrackSolver(problem)
    t0 = time.perf_counter()
    solutions = solver.solve(find_all=True)
    elapsed = time.perf_counter() - t0
    print_solver_result("Backtracking Solver", problem, solutions, elapsed)

def run_smart(problem):
    solver = SmartSolver(problem)
    t0 = time.perf_counter()
    solutions = solver.solve(find_all=True)
    elapsed = time.perf_counter() - t0
    print_solver_result("Smart Solver (with heuristics)", problem, solutions, elapsed)

def run_ortools(problem):
    solver = CpSatSolver(problem)
    t0 = time.perf_counter()
    solutions = solver.solve()
    elapsed = time.perf_counter() - t0
    print_solver_result("OR-Tools CP-SAT Solver", problem, solutions, elapsed)

if __name__ == "__main__":
    with open("game-samples/pips-board-10.json") as f:
        board = json.load(f)

    problem = PipsProblem(board)
    print(problem.summary())

    # run_backtrack(problem)
    # run_smart(problem)
    run_ortools(problem)
