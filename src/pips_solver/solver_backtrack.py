"""
solver_backtrack.py
-------------------
Pure-Python backtracking solver — no external dependencies required.

Uses constraint propagation: selects positions ensuring each variable
is covered exactly once and each domino is used exactly once.
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
    Enumerate all solutions by backtracking through:
      1. Position selections (which positions are used)
      2. Domino assignments (which domino for each position)
      3. Orientations (forward or reverse for each domino)

    Constraints:
      - Each variable covered exactly once
      - Each domino used exactly once
      - Area constraints satisfied
    """

    def __init__(self, problem: PipsProblem):
        self.prob = problem

    def solve(self, find_all: bool = False) -> list[Solution]:
        prob = self.prob
        results: list[Solution] = []
        
        n_pos = len(prob.positions)
        n_dom = len(prob.dominoes)
        
        # Try all 2^n_pos subsets of positions, filter for valid coverage
        for mask in range(1 << n_pos):
            selected_positions = [p for p in range(n_pos) if (mask >> p) & 1]
            
            # Must select exactly n_dom positions (one per domino)
            if len(selected_positions) != n_dom:
                continue
            
            # Check if selected positions cover all variables exactly once
            covered = [0] * prob.n
            for p in selected_positions:
                a, b = prob.positions[p]
                covered[a] += 1
                covered[b] += 1
            
            if covered != [1] * prob.n:
                continue
            
            # Valid position coverage. Now try domino assignments + orientations.
            for dom_perm in permutations(range(n_dom)):
                # Try all 2^n_dom orientation combinations
                for orient_bits in range(1 << n_dom):
                    vals = [None] * prob.n
                    ok = True
                    
                    for i, p in enumerate(selected_positions):
                        a, b = prob.positions[p]
                        lo, hi = prob.dominoes[dom_perm[i]]
                        
                        if (orient_bits >> i) & 1:
                            lo, hi = hi, lo
                        
                        # Domain check
                        if lo not in prob.domains[prob.variables[a]]:
                            ok = False
                            break
                        if hi not in prob.domains[prob.variables[b]]:
                            ok = False
                            break
                        
                        vals[a] = lo
                        vals[b] = hi
                    
                    if ok and prob.check_constraints(vals):
                        placement = [
                            (selected_positions[i], prob.dominoes[dom_perm[i]], 
                             prob.positions[selected_positions[i]])
                            for i in range(n_dom)
                        ]
                        results.append(Solution(vals, placement))
                        if not find_all:
                            return results

        return results
