"""
solver_backtrack.py
-------------------
Pure-Python backtracking solver — no external dependencies required.
"""

from itertools import permutations
from problem import PipsProblem


class Solution:
    def __init__(self, vals, placement):
        self.vals = vals            # list[int], length N
        self.placement = placement  # list of (pos_idx, domino, (a_val, b_val))

    def __repr__(self):
        lines = ["=== Solution ==="]
        lines.append(f"Values: {self.vals}")
        for pos_idx, domino, (a_idx, b_idx) in self.placement:
            lines.append(
                f"  p{pos_idx + 1} = "
                f"(x{a_idx + 1}={self.vals[a_idx]}, "
                f"x{b_idx + 1}={self.vals[b_idx]})  "
                f"<- domino {domino}"
            )
        return "\n".join(lines)


class BacktrackSolver:
    """
    Enumerate all solutions by:
      1. Iterating over valid position combos (guaranteed full coverage).
      2. Trying all permutations of domino → position assignments.
      3. Trying both orientations for each domino.
      4. Checking consistency eagerly and validating area constraints.
    """

    def __init__(self, problem: PipsProblem):
        self.prob = problem

    def solve(self, find_all: bool = False) -> list[Solution]:
        prob = self.prob
        results: list[Solution] = []

        for combo in prob.valid_combos:
            pos_pairs = [prob.positions[p] for p in combo]
            n_dom = len(prob.dominoes)

            for dom_perm in permutations(range(n_dom)):
                # 2^n_dom orientation combinations
                for orient_bits in range(1 << n_dom):
                    vals = [None] * prob.n
                    ok = True

                    for i, (a, b) in enumerate(pos_pairs):
                        lo, hi = prob.dominoes[dom_perm[i]]
                        if (orient_bits >> i) & 1:
                            lo, hi = hi, lo

                        # Domain check
                        if lo not in prob.domains[prob.variables[a]]:
                            ok = False; break
                        if hi not in prob.domains[prob.variables[b]]:
                            ok = False; break

                        # Consistency check
                        if vals[a] is not None and vals[a] != lo:
                            ok = False; break
                        if vals[b] is not None and vals[b] != hi:
                            ok = False; break

                        vals[a] = lo
                        vals[b] = hi

                    if ok and prob.check_constraints(vals):
                        placement = [
                            (combo[i], prob.dominoes[dom_perm[i]], pos_pairs[i])
                            for i in range(n_dom)
                        ]
                        results.append(Solution(vals, placement))
                        if not find_all:
                            return results

        return results
