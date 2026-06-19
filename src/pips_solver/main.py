"""
main.py
-------
Example usage: load a board JSON and solve with both solvers.
"""

import json
import time
from problem import PipsProblem
from solver_backtrack import BacktrackSolver
from solver_smart import SmartSolver

def run_backtrack(problem):
    print("\n── Backtracking Solver ──────────────────────────────────────")
    solver = BacktrackSolver(problem)
    t0 = time.perf_counter()
    solutions = solver.solve(find_all=True)
    elapsed = time.perf_counter() - t0
    print(f"Found {len(solutions)} solution(s) in {elapsed:.4f}s")
    for s in solutions:
        print(s)

def run_smart(problem):
    print("\n── Smart Solver (with heuristics) ─────────────────────────────")
    solver = SmartSolver(problem)
    t0 = time.perf_counter()
    solutions = solver.solve(find_all=True)
    elapsed = time.perf_counter() - t0
    print(f"Found {len(solutions)} solution(s) in {elapsed:.4f}s")
    for s in solutions:
        print(s)

def run_ortools(problem):
    print("\n── OR-Tools CP-SAT Solver ───────────────────────────────────")
    try:
        from solver_ortools import CpSatSolver
    except ImportError:
        print("ortools not installed. Run: pip install ortools")
        return
    solver = CpSatSolver(problem)
    t0 = time.perf_counter()
    solutions = solver.solve()
    elapsed = time.perf_counter() - t0
    print(f"Found {len(solutions)} solution(s) in {elapsed:.4f}s")
    for s in solutions:
        print(s)

if __name__ == "__main__":
    with open("game-samples/pips-board-7.json") as f:
        board = json.load(f)

    problem = PipsProblem(board)
    print(problem.summary())

    # run_backtrack(problem)
    # run_smart(problem)
    run_ortools(problem)
