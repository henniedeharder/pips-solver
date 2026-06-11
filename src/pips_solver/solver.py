"""
Pips Puzzle Solver

Solves dominoes placement puzzles with area constraints.
"""

from typing import List, Tuple, Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum
import json


class RuleType(Enum):
    """Types of area constraints."""
    ALL_EQUAL = "all-equal"
    ALL_UNEQUAL = "all-unequal"
    GREATER_THAN = "greater-than"
    LESS_THAN = "less-than"
    SUM_EQUALS = "sum-equals"


@dataclass
class Area:
    """Represents a constraint area on the board."""
    rule: RuleType
    value: Optional[int]
    cells: Set[Tuple[int, int]]

    def validate(self, cell_values: Dict[Tuple[int, int], int]) -> bool:
        """Check if the area satisfies its constraint."""
        values = [cell_values[cell] for cell in self.cells if cell in cell_values]
        assigned = len(values)
        total = len(self.cells)
        remaining = total - assigned

        if self.rule == RuleType.ALL_EQUAL:
            if assigned <= 1:
                return True
            return len(set(values)) == 1

        if self.rule == RuleType.ALL_UNEQUAL:
            return len(set(values)) == assigned

        if self.rule == RuleType.GREATER_THAN:
            return all(v > self.value for v in values)

        if self.rule == RuleType.LESS_THAN:
            return all(v < self.value for v in values)

        if self.rule == RuleType.SUM_EQUALS:
            current = sum(values)
            if current > self.value:
                return False
            if current + (6 * remaining) < self.value:
                return False
            if remaining == 0:
                return current == self.value
            return True

        return True


@dataclass
class Domino:
    """Represents a domino piece."""
    left: int
    right: int

    def __hash__(self):
        return hash((min(self.left, self.right), max(self.left, self.right)))

    def __eq__(self, other):
        if not isinstance(other, Domino):
            return False
        return (self.left == other.left and self.right == other.right) or \
               (self.left == other.right and self.right == other.left)


class PipsSolver:
    """Solver for pips dominoes puzzles."""

    def __init__(self, board_json: Dict):
        """Initialize solver from board JSON."""
        self.rows = board_json["rows"]
        self.cols = board_json["cols"]
        self.selected_cells = set(tuple(cell) for cell in board_json["selected"])
        self.areas = self._parse_areas(board_json["areas"])
        self.dominoes = [Domino(d[0], d[1]) for d in board_json["dominoes"]]

        self.placement: Dict[Tuple[int, int], Tuple[Domino, int]] = {}
        self.domino_count = {domino: 1 for domino in self.dominoes}
        self.ordered_cells = sorted(self.selected_cells)
        self.cell_to_area_indices: Dict[Tuple[int, int], List[int]] = {
            cell: [] for cell in self.selected_cells
        }
        for area_index, area in enumerate(self.areas):
            for cell in area.cells:
                if cell in self.cell_to_area_indices:
                    self.cell_to_area_indices[cell].append(area_index)

    def _parse_areas(self, areas_data: List[Dict]) -> List[Area]:
        """Parse areas from JSON."""
        areas = []
        for area_data in areas_data:
            rule = RuleType(area_data["rule"])
            value = area_data.get("value")
            cells = set(tuple(cell) for cell in area_data["cells"])
            areas.append(Area(rule, value, cells))
        return areas

    def _get_neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get valid neighboring cells."""
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if (nr, nc) in self.selected_cells and (nr, nc) not in self.placement:
                    neighbors.append((nr, nc))
        return neighbors

    def _get_valid_dominoes(self, cell1: Tuple[int, int], cell2: Tuple[int, int]) -> List[Tuple[Domino, int, int]]:
        """Get dominoes that can be placed on two cells."""
        valid = []
        val1, val2 = cell1, cell2
        for domino in self.dominoes:
            if self.domino_count[domino] == 0:
                continue
            # Check both orientations
            valid.append((domino, domino.left, domino.right))
            if domino.left != domino.right:
                valid.append((domino, domino.right, domino.left))
        return valid

    def _is_valid_placement(
        self,
        cell_values: Dict[Tuple[int, int], int],
        changed_cells: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
    ) -> bool:
        """Check if current placement is valid."""
        if changed_cells is None:
            area_indices = range(len(self.areas))
        else:
            impacted = set()
            for cell in changed_cells:
                impacted.update(self.cell_to_area_indices.get(cell, []))
            area_indices = impacted

        for area_index in area_indices:
            if not self.areas[area_index].validate(cell_values):
                return False
        return True

    def _get_legal_candidates_for_cell(
        self,
        cell: Tuple[int, int],
        cell_values: Dict[Tuple[int, int], int],
    ) -> List[Tuple[Tuple[int, int], Domino, int, int]]:
        """Return legal (neighbor, domino, val_for_cell, val_for_neighbor) candidates for a cell."""
        row, col = cell
        legal = []
        neighbors = sorted(self._get_neighbors(row, col))
        for neighbor in neighbors:
            valid_dominoes = self._get_valid_dominoes(cell, neighbor)
            for domino, val1, val2 in valid_dominoes:
                if self.domino_count[domino] == 0:
                    continue

                cell_values[cell] = val1
                cell_values[neighbor] = val2
                if self._is_valid_placement(cell_values, (cell, neighbor)):
                    legal.append((neighbor, domino, val1, val2))
                del cell_values[cell]
                del cell_values[neighbor]
        return legal

    def _choose_next_move_mrv(
        self,
        cell_values: Dict[Tuple[int, int], int],
    ) -> Optional[Tuple[Tuple[int, int], List[Tuple[Tuple[int, int], Domino, int, int]]]]:
        """Pick the next cell with minimum remaining legal values (MRV)."""
        best_cell = None
        best_candidates = None

        for cell in self.ordered_cells:
            if cell in self.placement:
                continue

            candidates = self._get_legal_candidates_for_cell(cell, cell_values)
            if not candidates:
                return cell, []

            if best_candidates is None or len(candidates) < len(best_candidates):
                best_cell = cell
                best_candidates = candidates
                if len(best_candidates) == 1:
                    break

        if best_cell is None or best_candidates is None:
            return None
        return best_cell, best_candidates

    def solve(
        self,
        cell_values: Optional[Dict[Tuple[int, int], int]] = None,
    ) -> Optional[Dict[Tuple[int, int], int]]:
        """Solve the puzzle using backtracking."""
        if cell_values is None:
            cell_values = {}

        if len(self.placement) == len(self.selected_cells):
            return dict(cell_values) if self._is_valid_placement(cell_values) else None

        move = self._choose_next_move_mrv(cell_values)
        if move is None:
            return dict(cell_values) if self._is_valid_placement(cell_values) else None

        cell, candidates = move
        if not candidates:
            return None

        for neighbor, domino, val1, val2 in candidates:
            # Place domino
            self.placement[cell] = (domino, val1)
            self.placement[neighbor] = (domino, val2)
            self.domino_count[domino] -= 1
            cell_values[cell] = val1
            cell_values[neighbor] = val2

            result = self.solve(cell_values)
            if result is not None:
                return result

            # Backtrack
            del self.placement[cell]
            del self.placement[neighbor]
            self.domino_count[domino] += 1
            del cell_values[cell]
            del cell_values[neighbor]

        return None

    def get_solution_grid(self) -> Optional[List[List[int]]]:
        """Get solution as 2D grid."""
        if not self.placement:
            return None

        grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        domino_id = 1

        processed = set()
        for (r, c), (domino, value) in sorted(self.placement.items()):
            if (r, c) in processed:
                continue
            processed.add((r, c))

            # Find the other cell of this domino
            for (r2, c2), (d2, v2) in self.placement.items():
                if (r2, c2) not in processed and d2 == domino:
                    processed.add((r2, c2))
                    grid[r][c] = domino_id
                    grid[r2][c2] = domino_id
                    domino_id += 1
                    break

        return grid


def solve_from_json(json_file: str) -> Optional[List[List[int]]]:
    """Solve puzzle from JSON file."""
    with open(json_file, 'r') as f:
        board = json.load(f)

    solver = PipsSolver(board)
    return solver.get_solution_grid()
