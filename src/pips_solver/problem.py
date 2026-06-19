"""
problem.py
----------
Parses a pips-board JSON and formulates the constraint problem instance.
"""

from itertools import combinations


class PipsProblem:
    """
    Takes a pips-board JSON dict and builds:
      - variables      : list of var names  ["x1", ..., "xN"]
      - domains        : dict var -> list of allowed values
      - constraints    : list of constraint dicts
      - positions      : all valid domino placements (adjacent cell pairs)
      - valid_combos   : position combos that cover every variable exactly once
      - dominoes       : the domino tiles to place
    """

    def __init__(self, board: dict):
        self.board = board
        self.dominoes = [tuple(d) for d in board["dominoes"]]

        # ── Cell → variable mapping (row-major, left-to-right) ──────────────
        selected = sorted(
            [tuple(c) for c in board["selected"]],
            key=lambda rc: (rc[0], rc[1]),
        )
        self.cell_to_var: dict[tuple, str] = {}
        self.var_to_cell: dict[str, tuple] = {}
        self.variables: list[str] = []

        for i, cell in enumerate(selected):
            name = f"x{i + 1}"
            self.cell_to_var[cell] = name
            self.var_to_cell[name] = cell
            self.variables.append(name)

        self.n = len(self.variables)
        self._var_index = {v: i for i, v in enumerate(self.variables)}

        # ── Domains ─────────────────────────────────────────────────────────
        self.domains: dict[str, list[int]] = {
            v: list(range(7)) for v in self.variables
        }

        # ── Constraints ─────────────────────────────────────────────────────
        self.constraints: list[dict] = []
        for area in board["areas"]:
            cells = [tuple(c) for c in area["cells"]]
            vars_ = [self.cell_to_var[c] for c in cells]
            self.constraints.append({
                "rule":  area["rule"],
                "value": area["value"],
                "vars":  vars_,
            })

        # ── Domino positions (adjacent selected cell pairs) ──────────────────
        cell_set = set(selected)
        positions = []
        seen = set()
        for cell in selected:
            r, c_ = cell
            for nr, nc in [(r, c_ + 1), (r + 1, c_)]:   # right / down
                neighbour = (nr, nc)
                if neighbour in cell_set:
                    pair = (cell, neighbour)
                    if pair not in seen:
                        seen.add(pair)
                        positions.append(pair)

        # Store as index pairs for efficiency
        self.position_cells: list[tuple[tuple, tuple]] = positions
        self.positions: list[tuple[int, int]] = [
            (self._var_index[self.cell_to_var[a]],
             self._var_index[self.cell_to_var[b]])
            for a, b in positions
        ]

        # ── Valid combos: sets of positions that cover all variables exactly once
        n_dom = len(self.dominoes)
        assert n_dom * 2 == self.n, (
            f"Expected {self.n // 2} dominoes to cover {self.n} variables, "
            f"got {n_dom}."
        )
        self.valid_combos: list[tuple[int, ...]] = [
            combo
            for combo in combinations(range(len(self.positions)), n_dom)
            if self._covers_all(combo)
        ]

    # ── helpers ─────────────────────────────────────────────────────────────

    def _covers_all(self, combo: tuple[int, ...]) -> bool:
        covered = []
        for p in combo:
            a, b = self.positions[p]
            covered.extend([a, b])
        return sorted(covered) == list(range(self.n))

    def check_constraints(self, vals: list[int]) -> bool:
        """Return True if vals satisfies all area constraints."""
        for c in self.constraints:
            indices = [self._var_index[v] for v in c["vars"]]
            rule = c["rule"]
            if rule == "less-than":
                if any(vals[i] >= c["value"] for i in indices):
                    return False
            elif rule == "all-equal":
                if len(set(vals[i] for i in indices)) > 1:
                    return False
            elif rule == "sum-equals":
                if sum(vals[i] for i in indices) != c["value"]:
                    return False
        return True

    def summary(self) -> str:
        lines = ["=== PipsProblem ==="]
        lines.append(f"Variables : {self.variables}")
        lines.append(f"Domains   : { {v: self.domains[v] for v in self.variables} }")
        lines.append("Constraints:")
        for c in self.constraints:
            lines.append(f"  {c['rule']} | vars={c['vars']} | value={c['value']}")
        lines.append(f"Positions ({len(self.positions)}):")
        for i, (a, b) in enumerate(self.positions):
            va, vb = self.variables[a], self.variables[b]
            lines.append(f"  p{i + 1} = ({va}, {vb})")
        lines.append(f"Valid position combos: {len(self.valid_combos)}")
        for combo in self.valid_combos:
            lines.append(f"  { ['p' + str(p + 1) for p in combo] }")
        lines.append(f"Dominoes  : {self.dominoes}")
        return "\n".join(lines)
