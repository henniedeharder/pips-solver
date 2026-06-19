"""
solver_ortools.py
-----------------
OR-Tools CP-SAT solver for the pips-board problem.
Requires: pip install ortools
"""

from ortools.sat.python import cp_model
from problem import PipsProblem
from solver_backtrack import Solution   # reuse the Solution dataclass


class CpSatSolver:
    """
    Builds a CP-SAT model from a PipsProblem instance and solves it.

    Model decisions
    ---------------
    x[i]          : IntVar in domain[i]          — pip value at cell i
    sel[p]        : BoolVar                       — position p is selected
    assign[p][d]  : BoolVar                       — position p uses domino d
    fwd[p][d]     : BoolVar                       — domino is placed in fwd orientation
    """

    def __init__(self, problem: PipsProblem):
        self.prob = problem

    def solve(self, time_limit_s: float = 30.0) -> list[Solution]:
        prob = self.prob
        model = cp_model.CpModel()

        # ── Variable nodes ───────────────────────────────────────────────────
        x = [
            model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(prob.domains[v]),
                v,
            )
            for v in prob.variables
        ]

        # ── Area constraints ─────────────────────────────────────────────────
        for c in prob.constraints:
            indices = [prob._var_index[v] for v in c["vars"]]
            rule, value = c["rule"], c["value"]

            if rule == "less-than":
                for i in indices:
                    model.Add(x[i] < value)
            elif rule == "all-equal":
                for i in indices[1:]:
                    model.Add(x[indices[0]] == x[i])
            elif rule == "sum-equals":
                model.Add(sum(x[i] for i in indices) == value)

        # ── Position selection ───────────────────────────────────────────────
        n_pos = len(prob.positions)
        n_dom = len(prob.dominoes)

        sel = [model.NewBoolVar(f"sel_p{p + 1}") for p in range(n_pos)]

        # Each variable covered by exactly one selected position
        for var_idx in range(prob.n):
            covering = [sel[p] for p, (a, b) in enumerate(prob.positions)
                        if a == var_idx or b == var_idx]
            model.Add(sum(covering) == 1)

        # ── Domino assignment ────────────────────────────────────────────────
        assign = []
        fwd    = []
        for p, (a, b) in enumerate(prob.positions):
            assign_row = [model.NewBoolVar(f"asgn_p{p+1}_d{d+1}") for d in range(n_dom)]
            fwd_row    = [model.NewBoolVar(f"fwd_p{p+1}_d{d+1}")   for d in range(n_dom)]
            assign.append(assign_row)
            fwd.append(fwd_row)

            # Exactly one domino if selected, none otherwise
            model.Add(sum(assign_row) == 1).OnlyEnforceIf(sel[p])
            model.Add(sum(assign_row) == 0).OnlyEnforceIf(sel[p].Not())

            for d, (lo, hi) in enumerate(prob.dominoes):
                # fwd/bwd only active when assigned
                model.Add(fwd_row[d] == 0).OnlyEnforceIf(assign_row[d].Not())

                # Forward: x[a]=lo, x[b]=hi
                model.Add(x[a] == lo).OnlyEnforceIf([assign_row[d], fwd_row[d]])
                model.Add(x[b] == hi).OnlyEnforceIf([assign_row[d], fwd_row[d]])

                # Backward: x[a]=hi, x[b]=lo
                bwd = fwd_row[d].Not()
                model.Add(x[a] == hi).OnlyEnforceIf([assign_row[d], bwd])
                model.Add(x[b] == lo).OnlyEnforceIf([assign_row[d], bwd])

        # Each domino used exactly once
        for d in range(n_dom):
            model.Add(sum(assign[p][d] for p in range(n_pos)) == 1)

        # ── Solve ────────────────────────────────────────────────────────────
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_s
        solver.parameters.log_search_progress = False

        results: list[Solution] = []

        status = solver.Solve(model)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            vals = [solver.Value(xi) for xi in x]
            placement = []
            for p, (a, b) in enumerate(prob.positions):
                if solver.Value(sel[p]):
                    for d in range(n_dom):
                        if solver.Value(assign[p][d]):
                            placement.append(
                                (p, prob.dominoes[d], (a, b))
                            )
            results.append(Solution(vals, placement))

        return results
