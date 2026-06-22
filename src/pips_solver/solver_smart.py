"""
solver_smart.py
---------------
A fast custom constraint-propagation solver for the pips-board problem.

Techniques used
---------------
1. Arc Consistency (AC-3 style)  — propagate area constraints to fixpoint
2. Domino-aware domain filtering — restrict variable domains to values that
                                   appear in at least one still-available
                                   domino tile for every position they belong to
3. Unit propagation              — if only one (domino, orientation) fits a
                                   position, assign it immediately (cascade)
4. MRV (Minimum Remaining Values)— branch on the position with fewest valid
                                   (domino, orientation) options first
5. Forward checking              — after every assignment, propagate immediately
                                   and prune; fail fast on empty domain
6. Chronological backtracking    — with cheap clone-based state snapshots
"""

from __future__ import annotations
from problem import PipsProblem


# ─────────────────────────────────────────────────────────────────────────────
# Internal state (mutable during search, cheap to clone)
# ─────────────────────────────────────────────────────────────────────────────

class _State:
    """All mutable solver state in one object for O(n) snapshotting."""
    __slots__ = ("vals", "domains", "dom_available", "pos_assigned")

    def __init__(self, n_vars: int, n_dom: int, domains: dict[str, list[int]]):
        self.vals: list[int | None] = [None] * n_vars  # assigned pip values
        self.domains       = [set(d) for d in domains.values()]   # domain per var
        self.dom_available = set(range(n_dom))      # domino indices not yet placed
        self.pos_assigned  = {}                     # pos_idx -> domino_idx

    def clone(self) -> "_State":
        s = object.__new__(_State)
        s.vals = self.vals[:]
        s.domains       = [d.copy() for d in self.domains]
        s.dom_available = self.dom_available.copy()
        s.pos_assigned  = self.pos_assigned.copy()
        return s


# ─────────────────────────────────────────────────────────────────────────────
# Solver
# ─────────────────────────────────────────────────────────────────────────────

class SmartSolver:
    """
    Custom propagation + backtracking solver for PipsProblem.

    Uses constraint propagation to naturally find valid position selections where:
      - Each variable is covered exactly once
      - Each domino is used exactly once
      - Area constraints are satisfied
    """

    def __init__(self, problem: PipsProblem):
        self.prob = problem
        # Precompute options per position: list of (domino_idx, val_a, val_b)
        self.pos_options: list[list[tuple[int, int, int]]] = []
        for (a, b) in problem.positions:
            opts = []
            for d_idx, (lo, hi) in enumerate(problem.dominoes):
                opts.append((d_idx, lo, hi))
                if lo != hi:
                    opts.append((d_idx, hi, lo))
            self.pos_options.append(opts)

    # ── Public API ────────────────────────────────────────────────────────────

    def solve(self, find_all: bool = False) -> list[dict]:
        """
        Returns a list of solution dicts:
          {
            "vals":      list[int],            # pip value per variable (x1..xN)
            "placement": list of (pos_idx, domino_tuple, (a_idx, b_idx))
          }
        """
        results: list[dict] = []
        prob = self.prob
        
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
            
            # Valid position coverage. Use propagation to speed up domino search.
            state = _State(
                prob.n, len(prob.dominoes),
                {v: prob.domains[v] for v in prob.variables}
            )
            
            ok, unassigned = self._propagate(state, selected_positions[:])
            if not ok:
                continue
            
            # Now search for domino assignments within this position combo
            self._search_combo(state, selected_positions, unassigned, results, find_all)
            if not find_all and results:
                return results

        return results

    def _search_combo(self, state: _State, combo: list[int], 
                      unassigned: list[int], results: list, find_all: bool) -> None:
        """Search for valid domino assignments within a fixed position combo."""
        prob = self.prob
        
        if not unassigned:
            if all(v is not None for v in state.vals) and \
               len(state.dom_available) == 0:
                typed_vals = [value for value in state.vals if value is not None]
                if prob.check_constraints(typed_vals):
                    placement = [
                        (p, prob.dominoes[state.pos_assigned[p]],
                         prob.positions[p])
                        for p in sorted(state.pos_assigned.keys())
                    ]
                    results.append({"vals": typed_vals, "placement": placement})
                
            return
        
        # MRV: pick the tightest unassigned position
        pos_idx = self._mrv(state, unassigned)
        remaining = [p for p in unassigned if p != pos_idx]
        a, b = prob.positions[pos_idx]
        
        # Try to assign this position with various dominoes
        for d_idx, lo, hi in self.pos_options[pos_idx]:
            if d_idx not in state.dom_available:
                continue
            if lo not in state.domains[a] or hi not in state.domains[b]:
                continue
            
            saved = state.clone()
            
            # Assign
            state.vals[a] = lo
            state.vals[b] = hi
            state.domains[a] = {lo}
            state.domains[b] = {hi}
            state.dom_available.discard(d_idx)
            state.pos_assigned[pos_idx] = d_idx
            
            ok, new_remaining = self._propagate(state, remaining)
            if ok:
                self._search_combo(state, combo, new_remaining, results, find_all)
                if not find_all and results:
                    return
            
            # Restore
            state.vals          = saved.vals
            state.domains       = saved.domains
            state.dom_available = saved.dom_available
            state.pos_assigned  = saved.pos_assigned

    # ── MRV heuristic ─────────────────────────────────────────────────────────

    def _mrv(self, state: _State, unassigned: list[int]) -> int:
        """Pick the position with fewest valid (domino, orientation) options."""
        best_pos   = unassigned[0]
        best_count = float("inf")
        for p in unassigned:
            a, b = self.prob.positions[p]
            count = sum(
                1 for d_idx, lo, hi in self.pos_options[p]
                if d_idx in state.dom_available
                and lo in state.domains[a]
                and hi in state.domains[b]
            )
            if count < best_count:
                best_count, best_pos = count, p
                if count <= 1:
                    break   # can't do better; 0 means dead end (caught in propagate)
        return best_pos

    # ── Propagation ───────────────────────────────────────────────────────────

    def _propagate(self, state: _State,
                   unassigned: list[int]) -> tuple[bool, list[int]]:
        """
        Run propagation to fixpoint.
        Returns (feasible, updated_unassigned_list).
        """
        changed = True
        while changed:
            changed = False

            if not self._propagate_areas(state):
                return False, unassigned

            c, ch, unassigned = self._propagate_dominoes(state, unassigned)
            if not c:
                return False, unassigned
            changed = changed or ch

        return True, unassigned

    def _propagate_areas(self, state: _State) -> bool:
        """AC-3-style propagation of area constraints."""
        prob = self.prob
        changed = True
        while changed:
            changed = False
            for c in prob.constraints:
                idxs  = [prob._var_index[v] for v in c["vars"]]
                rule  = c["rule"]
                value = c["value"]

                if rule == "less-than":
                    for i in idxs:
                        new = {x for x in state.domains[i] if x < value}
                        if new != state.domains[i]:
                            if not new:
                                return False
                            state.domains[i] = new
                            changed = True

                elif rule == "all-equal":
                    common = state.domains[idxs[0]].copy()
                    for i in idxs[1:]:
                        common &= state.domains[i]
                    if not common:
                        return False
                    for i in idxs:
                        if state.domains[i] != common:
                            state.domains[i] = common.copy()
                            changed = True

                elif rule == "sum-equals":
                    if len(idxs) == 2:
                        i, j = idxs
                        new_i = {v for v in state.domains[i]
                                 if (value - v) in state.domains[j]}
                        new_j = {v for v in state.domains[j]
                                 if (value - v) in state.domains[i]}
                        if not new_i or not new_j:
                            return False
                        if new_i != state.domains[i]:
                            state.domains[i] = new_i
                            changed = True
                        if new_j != state.domains[j]:
                            state.domains[j] = new_j
                            changed = True
        return True

    def _propagate_dominoes(self, state: _State,
                             unassigned: list[int]) -> tuple[bool, bool, list[int]]:
        """
        For each unassigned position:
          - Restrict variable domains to values reachable by an available domino.
          - If exactly one option remains → assign it (unit propagation).
        Cascades until fixpoint.
        Returns (feasible, changed, updated_unassigned).
        """
        any_changed = True
        overall_changed = False

        while any_changed:
            any_changed = False
            next_unassigned = []

            for p in unassigned:
                a, b = self.prob.positions[p]
                fits = [
                    (d_idx, lo, hi)
                    for d_idx, lo, hi in self.pos_options[p]
                    if d_idx in state.dom_available
                    and lo in state.domains[a]
                    and hi in state.domains[b]
                ]

                if not fits:
                    return False, overall_changed, unassigned

                # Restrict domains to reachable values
                ra = {lo for _, lo, _ in fits}
                rb = {hi for _, _, hi in fits}

                if ra != state.domains[a]:
                    state.domains[a] = ra
                    any_changed = True
                if rb != state.domains[b]:
                    state.domains[b] = rb
                    any_changed = True

                # Unit propagation
                if len(fits) == 1:
                    d_idx, lo, hi = fits[0]
                    state.vals[a] = lo
                    state.vals[b] = hi
                    state.domains[a] = {lo}
                    state.domains[b] = {hi}
                    state.dom_available.discard(d_idx)
                    state.pos_assigned[p] = d_idx
                    any_changed = True
                    overall_changed = True
                    # Don't add to next_unassigned — it's now assigned
                else:
                    next_unassigned.append(p)

            unassigned = next_unassigned
            overall_changed = overall_changed or any_changed

        return True, overall_changed, unassigned


# ─────────────────────────────────────────────────────────────────────────────
# Solution wrapper
# ─────────────────────────────────────────────────────────────────────────────

class Solution:
    def __init__(self, raw: dict, problem: PipsProblem):
        self.vals      = raw["vals"]
        self.placement = raw["placement"]
        self._prob     = problem

    def __repr__(self) -> str:
        prob  = self._prob
        lines = ["=== Solution ==="]
        lines.append("  " + "  ".join(
            f"{v}={val}" for v, val in zip(prob.variables, self.vals)
        ))
        for pos_idx, domino, (a, b) in self.placement:
            lines.append(
                f"  p{pos_idx + 1} = "
                f"({prob.variables[a]}={self.vals[a]}, "
                f"{prob.variables[b]}={self.vals[b]})  "
                f"<- domino {domino}"
            )
        return "\n".join(lines)
