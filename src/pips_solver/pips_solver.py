import json
import time
from collections import defaultdict
from pathlib import Path

PIP_MAX = 6

class DominoSuperSolver:
    def __init__(self, board_data):
        self.rows      = board_data["rows"]
        self.cols      = board_data["cols"]
        self.selected  = set(tuple(c) for c in board_data["selected"])
        self.areas     = board_data["areas"]
        self.pool      = [tuple(d) for d in board_data["dominoes"]]
        self.selected_list = board_data["selected"]  # Keep original list for later

        self.board = {}
        for r in range(self.rows):
            for c in range(self.cols):
                self.board[(r,c)] = None if (r,c) in self.selected else -1

        self.ordered_cells = sorted(self.selected, key=lambda x: (x[0], x[1]))

        self.cell_areas = defaultdict(list)
        for idx, area in enumerate(self.areas):
            for cell in area["cells"]:
                self.cell_areas[tuple(cell)].append(idx)

        self.stats = {
            "nodes": 0,
            "backtracks": 0,
            "elapsed": 0.0,
            "nodes_visited": 0,
            "candidate_checks": 0,
            "placements_tried": 0,
            "dead_ends": 0,
            "max_depth": 0,
        }
        # Compact steps: only keep place/backtrack events, NOT full board copies
        self.steps = []
        self.tested_dominoes_order = []
        self.solution_board      = None
        self.solution_placements = []
        self.solution_steps = []  # Will store steps in frontend format

    def _area_ok(self, area_idx, partial=True):
        area  = self.areas[area_idx]
        rule  = area["rule"]
        val   = area["value"]
        cells = [tuple(c) for c in area["cells"]]
        pips  = [self.board[c] for c in cells]
        filled   = [p for p in pips if p is not None]
        n_total  = len(cells)
        n_filled = len(filled)

        if rule == "sum-equals":
            s = sum(filled)
            if s > val: return False
            if partial and n_filled < n_total:
                remaining = n_total - n_filled
                if s + remaining * PIP_MAX < val: return False
                return True
            return s == val
        elif rule == "all-equal":
            return len(set(filled)) <= 1
        elif rule == "all-unequal":
            return len(set(filled)) == n_filled
        elif rule == "greater-than":
            s = sum(filled)
            if partial and n_filled < n_total: return True
            return s > val
        elif rule == "less-than":
            s = sum(filled)
            if partial and n_filled < n_total:
                return s < val
            return s < val
        return True

    def _constraints_ok(self, changed_cells, partial=True):
        seen = set()
        for cell in changed_cells:
            for aidx in self.cell_areas[cell]:
                if aidx not in seen:
                    seen.add(aidx)
                    if not self._area_ok(aidx, partial=partial):
                        return False
        return True

    def _all_constraints_ok(self):
        return all(self._area_ok(i, partial=False) for i in range(len(self.areas)))

    def _first_empty(self):
        for cell in self.ordered_cells:
            if self.board[cell] is None:
                return cell
        return None

    def _neighbour_cells(self, r, c):
        candidates = [(r, c+1), (r+1, c)]
        return [(nr, nc) for nr, nc in candidates
                if (nr, nc) in self.selected and self.board[(nr,nc)] is None]

    def _search(self, depth=0):
        self.stats["nodes"] += 1
        self.stats["nodes_visited"] += 1
        if depth > self.stats["max_depth"]:
            self.stats["max_depth"] = depth

        cell = self._first_empty()
        if cell is None:
            return self._all_constraints_ok()

        r, c = cell
        neighbours = self._neighbour_cells(r, c)
        if not neighbours:
            self.stats["dead_ends"] += 1
            return False   # isolated cell → dead end

        tried = set()
        for dom_idx, (a, b) in enumerate(self.pool):
            orientations = [(a, b)] if a == b else [(a, b), (b, a)]
            for p1, p2 in orientations:
                key = (dom_idx, p1, p2)
                if key in tried: continue
                tried.add(key)

                for (r2, c2) in neighbours:
                    self.stats["candidate_checks"] += 1
                    self.board[(r,c)]   = p1
                    self.board[(r2,c2)] = p2
                    dom = self.pool.pop(dom_idx)

                    self.steps.append({"action":"place","domino":[a,b],
                                       "cells":[[r,c,p1],[r2,c2,p2]],
                                       "pool_left":len(self.pool)})

                    is_valid = self._constraints_ok({(r,c),(r2,c2)}, partial=True)
                    self.tested_dominoes_order.append({
                        "depth": depth,
                        "cell": [r, c],
                        "neighbor": [r2, c2],
                        "domino": [a, b],
                        "values": [p1, p2],
                        "accepted": is_valid,
                    })

                    if is_valid:
                        self.stats["placements_tried"] += 1
                        if self._search(depth + 1):
                            self.solution_placements.append(((a,b),(r,c),(r2,c2)))
                            return True

                    self.stats["backtracks"] += 1
                    self.steps.append({"action":"backtrack","domino":[a,b],
                                       "cells":[[r,c],[r2,c2]]})
                    self.board[(r,c)]   = None
                    self.board[(r2,c2)] = None
                    self.pool.insert(dom_idx, dom)

        return False

    def solve(self):
        t0 = time.time()
        found = self._search(depth=0)
        self.stats["elapsed"] = round(time.time() - t0, 6)
        if found:
            self.solution_board = [[self.board.get((r,c), -1) for c in range(self.cols)]
                                   for r in range(self.rows)]
            self._convert_steps_to_frontend_format()
        return found
    
    def _convert_steps_to_frontend_format(self):
        """Convert internal steps to frontend-compatible format."""
        # Keep only the final solved path order (root -> leaf)
        self.solution_steps = []
        final_path = list(reversed(self.solution_placements))
        for depth, (domino, cell1, cell2) in enumerate(final_path):
            v1 = self.board[cell1]
            v2 = self.board[cell2]
            self.solution_steps.append({
                "depth": depth,
                "cell": [cell1[0], cell1[1]],
                "neighbor": [cell2[0], cell2[1]],
                "domino": [domino[0], domino[1]],
                "values": [v1, v2],
            })
    
    def print_solution_board(self, selected=None):
        """Print the solution board nicely."""
        if not self.solution_board:
            print("No solution found.")
            return
        
        if selected is None:
            selected = self.selected_list
            
        if selected:
            min_row = min(cell[0] for cell in selected)
            max_row = max(cell[0] for cell in selected)
            min_col = min(cell[1] for cell in selected)
            max_col = max(cell[1] for cell in selected)
        else:
            min_row = 0
            max_row = self.rows - 1
            min_col = 0
            max_col = self.cols - 1
        
        value_map = {}
        for r, c in self.selected:
            value_map[(r, c)] = self.board.get((r, c), -1)
        
        print("\nSolved Value Board:")
        for row in range(min_row, max_row + 1):
            row_values = []
            for col in range(min_col, max_col + 1):
                if (row, col) in self.selected:
                    row_values.append(str(value_map.get((row, col), "")))
                else:
                    row_values.append("")
            line = "  ".join(f"{value:>2}" for value in row_values)
            print(f"  {line}")
        
        print("\nDomino Layout Grid:")
        for row in range(min_row, max_row + 1):
            row_values = []
            for col in range(min_col, max_col + 1):
                value = self.solution_board[row][col] if row < len(self.solution_board) and col < len(self.solution_board[row]) else 0
                row_values.append("" if value <= 0 else str(value))
            line = "  ".join(f"{value:>2}" for value in row_values)
            print(f"  {line}")
    
    def get_solution_dict(self):
        """Get solution as a dict mapping cell tuples to values."""
        if not self.board:
            return {}
        solution = {}
        for cell in self.selected:
            solution[str(cell)] = self.board.get(cell)
        return solution

    def get_search_stats(self):
        """Return a copy of search stats."""
        return dict(self.stats)

    def get_tested_dominoes_order(self):
        """Return tested domino attempts in search order."""
        return list(self.tested_dominoes_order)
    
    def save_solution(self, output_file):
        """Save solution to JSON file in expected format."""
        if not self.solution_board:
            result = {
                "status": "no_solution",
                "search_stats": self.get_search_stats(),
                "tested_dominoes_order": self.get_tested_dominoes_order(),
            }
        else:
            result = {
                "status": "solved",
                "solution": self.get_solution_dict(),
                "solution_steps": self.solution_steps,
                "search_stats": self.get_search_stats(),
                "tested_dominoes_order": self.get_tested_dominoes_order(),
            }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result