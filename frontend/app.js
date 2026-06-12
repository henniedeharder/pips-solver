const boardEl = document.getElementById("board");
const rowsInput = document.getElementById("rowsInput");
const colsInput = document.getElementById("colsInput");
const rebuildBtn = document.getElementById("rebuildBtn");
const toggleRevealBtn = document.getElementById("toggleRevealBtn");
const readyBtn = document.getElementById("readyBtn");
const playBackBtn = document.getElementById("playBackBtn");
const clearBtn = document.getElementById("clearBtn");
const hintBtn = document.getElementById("hintBtn");
const solutionBtn = document.getElementById("solutionBtn");
const processBtn = document.getElementById("processBtn");
const statsBtn = document.getElementById("statsBtn");
const boardHintEl = document.getElementById("boardHint");
const areasListEl = document.getElementById("areasList");
const ruleButtons = Array.from(document.querySelectorAll(".rule-btn"));
const dominoesEl = document.getElementById("dominoes");

const AREA_PALETTE = [
  { border: "#2a9d8f", bg: "#e4f5f2" },
  { border: "#e76f51", bg: "#fde9e5" },
  { border: "#1d3557", bg: "#e7edf7" },
  { border: "#8e44ad", bg: "#efe6f6" },
  { border: "#f4a261", bg: "#fff2e5" },
  { border: "#0f4c5c", bg: "#dfedf1" },
];

const state = {
  rows: 10,
  cols: 10,
  selected: new Set(),
  reveal: false,
  ready: false,
  drag: {
    active: false,
    mode: "add",
    visited: new Set(),
  },
  areaDraft: new Set(),
  areas: [],
  cellArea: new Map(),
  nextAreaId: 1,
  selectedDominoes: new Set(),
  solveData: null,
  hintedSteps: 0,
  processTimer: null,
  processRunId: 0,
};

const solveStatus = document.getElementById("solveStatus");

const cellEls = new Map();

function keyFor(row, col) {
  return `${row}:${col}`;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function areaMarker(area) {
  if (area.rule === "all-equal") {
    return "=";
  }
  if (area.rule === "all-unequal") {
    return "!=";
  }
  if (area.rule === "greater-than") {
    return `>${area.value}`;
  }
  if (area.rule === "less-than") {
    return `<${area.value}`;
  }
  return String(area.value);
}

function formatAreaRule(area) {
  if (area.rule === "all-equal") {
    return "all equal";
  }
  if (area.rule === "all-unequal") {
    return "all unequal";
  }
  if (area.rule === "greater-than") {
    return `>${area.value}`;
  }
  if (area.rule === "less-than") {
    return `<${area.value}`;
  }
  return `sum=${area.value}`;
}

function getAreaById(id) {
  return state.areas.find((area) => area.id === id) || null;
}

function removeCellFromArea(key) {
  const prevAreaId = state.cellArea.get(key);
  if (!prevAreaId) {
    return;
  }

  const prevArea = getAreaById(prevAreaId);
  if (prevArea) {
    prevArea.cells = prevArea.cells.filter((existing) => existing !== key);
    if (prevArea.anchor === key) {
      prevArea.anchor = prevArea.cells[0] || null;
    }
  }
  state.cellArea.delete(key);
  state.areas = state.areas.filter((area) => area.cells.length > 0);
}

function setCellSelectionByKey(key, shouldSelect) {
  if (shouldSelect) {
    state.selected.add(key);
  } else {
    state.selected.delete(key);
    state.areaDraft.delete(key);
    removeCellFromArea(key);
  }
}

function updateCellVisualByKey(key) {
  const cell = cellEls.get(key);
  if (!cell) {
    return;
  }

  const selected = state.selected.has(key);
  const inDraft = state.areaDraft.has(key);
  const areaId = state.cellArea.get(key);
  const area = areaId ? getAreaById(areaId) : null;

  cell.className = "cell";
  if (selected) {
    cell.classList.add("selected");
  }
  if (inDraft) {
    cell.classList.add("area-draft");
  }
  if (area) {
    cell.classList.add("in-area");
    cell.style.setProperty("--area-color", area.color.border);
    cell.style.setProperty("--area-bg", area.color.bg);
    if (area.anchor === key) {
      cell.classList.add("area-anchor");
      cell.dataset.areaLabel = areaMarker(area);
    } else {
      delete cell.dataset.areaLabel;
    }
  } else {
    cell.style.removeProperty("--area-color");
    cell.style.removeProperty("--area-bg");
    delete cell.dataset.areaLabel;
  }
}

function refreshAllCells() {
  cellEls.forEach((_, key) => {
    updateCellVisualByKey(key);
  });
}

function updateBoardModeUi() {
  const showReveal = state.reveal || state.ready;
  boardEl.classList.toggle("reveal", showReveal);
  boardEl.classList.toggle("ready", state.ready);
  toggleRevealBtn.textContent = state.reveal ? "Back To Edit" : "Show Selected Board";
  readyBtn.textContent = state.ready ? "Back to Builder" : "Ready to play!";

  if (state.ready) {
    boardHintEl.textContent = "Ready mode: board and selected dominoes only.";
  } else if (state.reveal) {
    boardHintEl.textContent = "Click or drag selected squares to draft an area, then apply a rule.";
  } else {
    boardHintEl.textContent = "Click or drag squares to paint selection.";
  }

  document.querySelector(".app-shell").classList.toggle("ready-mode", state.ready);
}

function clearBoardLabels() {
  cellEls.forEach((cell) => {
    cell.textContent = "";
    cell.classList.remove("wrong-attempt");
  });
}

function stopProcessPlayback() {
  state.processRunId += 1;
  if (state.processTimer) {
    window.clearTimeout(state.processTimer);
    state.processTimer = null;
  }
}

function setPlayButtonsDisabled(disabled) {
  hintBtn.disabled = disabled;
  solutionBtn.disabled = disabled;
  processBtn.disabled = disabled;
  statsBtn.disabled = disabled;
}

function getSolveSteps() {
  if (!state.solveData || !Array.isArray(state.solveData.solution_steps)) {
    return [];
  }
  return state.solveData.solution_steps;
}

function getProcessAttempts() {
  if (!state.solveData || !Array.isArray(state.solveData.tested_dominoes_order)) {
    return [];
  }

  // Keep process playback readable: show actual placed candidates (accepted), including wrong ones later removed.
  return state.solveData.tested_dominoes_order.filter((attempt) => attempt.accepted === true);
}

function placementSignature(cellA, cellB, valueA, valueB) {
  const [r1, c1] = cellA;
  const [r2, c2] = cellB;
  const firstIsA = r1 < r2 || (r1 === r2 && c1 <= c2);
  if (firstIsA) {
    return `${r1}:${c1}:${valueA}|${r2}:${c2}:${valueB}`;
  }
  return `${r2}:${c2}:${valueB}|${r1}:${c1}:${valueA}`;
}

function getFinalPlacementSet() {
  const set = new Set();
  const steps = getSolveSteps();
  steps.forEach((step) => {
    const [v1, v2] = step.values;
    set.add(placementSignature(step.cell, step.neighbor, v1, v2));
  });
  return set;
}

function renderFixedValueMap(fixedValues) {
  clearBoardLabels();
  boardEl.classList.add("solved");
  fixedValues.forEach((value, key) => {
    const cell = cellEls.get(key);
    if (cell) {
      cell.textContent = String(value);
    }
  });
}

function paintAttempt(attempt, wrong) {
  const [r1, c1] = attempt.cell;
  const [r2, c2] = attempt.neighbor;
  const [v1, v2] = attempt.values;
  const key1 = keyFor(r1, c1);
  const key2 = keyFor(r2, c2);
  const cell1 = cellEls.get(key1);
  const cell2 = cellEls.get(key2);

  if (cell1) {
    cell1.textContent = String(v1);
    cell1.classList.toggle("wrong-attempt", wrong);
  }
  if (cell2) {
    cell2.textContent = String(v2);
    cell2.classList.toggle("wrong-attempt", wrong);
  }
}

function renderSolvedSteps(stepCount) {
  clearBoardLabels();
  const steps = getSolveSteps();
  const revealCount = clamp(stepCount, 0, steps.length);
  if (revealCount < 1) {
    return;
  }

  boardEl.classList.add("solved");
  for (let i = 0; i < revealCount; i += 1) {
    const step = steps[i];
    const [r1, c1] = step.cell;
    const [r2, c2] = step.neighbor;
    const [v1, v2] = step.values;
    const key1 = keyFor(r1, c1);
    const key2 = keyFor(r2, c2);
    const cell1 = cellEls.get(key1);
    const cell2 = cellEls.get(key2);
    if (cell1) {
      cell1.textContent = String(v1);
    }
    if (cell2) {
      cell2.textContent = String(v2);
    }
  }
}

function showSearchStats() {
  if (!state.solveData || !state.solveData.search_stats) {
    solveStatus.textContent = "No search stats available yet.";
    return;
  }

  const s = state.solveData.search_stats;
  const tested = Array.isArray(state.solveData.tested_dominoes_order)
    ? state.solveData.tested_dominoes_order.length
    : 0;

  solveStatus.textContent =
    `nodes=${s.nodes_visited}, checks=${s.candidate_checks}, tries=${s.placements_tried}, ` +
    `dead_ends=${s.dead_ends}, backtracks=${s.backtracks}, max_depth=${s.max_depth}, tested=${tested}, elapsed=${s.elapsed.toFixed(3)}s`;
}

function normalizeSolveData(rawData) {
  const data = rawData && typeof rawData === "object" ? { ...rawData } : {};

  const solutionSteps = Array.isArray(data.solution_steps) ? data.solution_steps : [];
  let testedOrder = Array.isArray(data.tested_dominoes_order) ? data.tested_dominoes_order : [];

  // Backward compatibility: derive attempts from legacy compact step log if needed.
  if (testedOrder.length === 0 && Array.isArray(data.steps)) {
    testedOrder = data.steps
      .filter((step) => step && step.action === "place" && Array.isArray(step.cells) && step.cells.length === 2)
      .map((step, index) => {
        const [a, b] = step.cells;
        return {
          depth: Number.isFinite(step.depth) ? step.depth : index,
          cell: [a[0], a[1]],
          neighbor: [b[0], b[1]],
          domino: Array.isArray(step.domino) ? step.domino : [0, 0],
          values: [a[2], b[2]],
          accepted: true,
        };
      });
  }

  const rawStats = data.search_stats && typeof data.search_stats === "object"
    ? data.search_stats
    : {};

  const acceptedCount = testedOrder.filter((attempt) => attempt && attempt.accepted === true).length;
  const maxDepthFromSteps = solutionSteps.length > 0
    ? Math.max(...solutionSteps.map((step, index) => (Number.isFinite(step.depth) ? step.depth : index)))
    : 0;

  data.solution_steps = solutionSteps;
  data.tested_dominoes_order = testedOrder;
  data.search_stats = {
    nodes_visited: Number.isFinite(rawStats.nodes_visited) ? rawStats.nodes_visited : (Number.isFinite(rawStats.nodes) ? rawStats.nodes : 0),
    candidate_checks: Number.isFinite(rawStats.candidate_checks) ? rawStats.candidate_checks : testedOrder.length,
    placements_tried: Number.isFinite(rawStats.placements_tried) ? rawStats.placements_tried : acceptedCount,
    dead_ends: Number.isFinite(rawStats.dead_ends) ? rawStats.dead_ends : 0,
    backtracks: Number.isFinite(rawStats.backtracks) ? rawStats.backtracks : 0,
    max_depth: Number.isFinite(rawStats.max_depth) ? rawStats.max_depth : maxDepthFromSteps,
    elapsed: Number.isFinite(rawStats.elapsed) ? rawStats.elapsed : 0,
    nodes: Number.isFinite(rawStats.nodes) ? rawStats.nodes : (Number.isFinite(rawStats.nodes_visited) ? rawStats.nodes_visited : 0),
  };

  return data;
}

function getApiUrl(path) {
  if (window.location.protocol === "file:") {
    throw new Error("API unavailable on file://. Start 'poetry run pips-server' and open http://127.0.0.1:8000/");
  }
  return new URL(path, window.location.origin).toString();
}

async function solveBoardInBackground() {
  const board = exportBoardAsJson();
  setPlayButtonsDisabled(true);
  solveStatus.textContent = "Solving in background...";
  state.solveData = null;
  state.hintedSteps = 0;
  stopProcessPlayback();
  clearBoardLabels();
  boardEl.classList.remove("solved");

  try {
    const response = await fetch(getApiUrl("/api/solve"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(board),
    });

    const data = normalizeSolveData(await response.json());
    state.solveData = data;

    if (data.status === "solved") {
      solveStatus.textContent = "Solved in background. Use Hint, Solution, or Process.";
      setPlayButtonsDisabled(false);
    } else if (data.status === "no_solution") {
      solveStatus.textContent = "No solution found for this puzzle.";
      statsBtn.disabled = false;
    } else {
      solveStatus.textContent = `Solve error: ${data.error || "Unknown error"}`;
      statsBtn.disabled = false;
    }
  } catch (error) {
    solveStatus.textContent = `Network error: ${error.message}`;
    statsBtn.disabled = true;
  }
}

function renderAreasList() {
  areasListEl.innerHTML = "";
  state.areas.forEach((area) => {
    const chip = document.createElement("span");
    chip.className = "area-chip";
    chip.style.setProperty("--area-color", area.color.border);
    chip.textContent = `${areaMarker(area)} [${area.cells.length}]`;
    areasListEl.appendChild(chip);
  });
}

function toggleAreaDraftCell(row, col) {
  if (!state.reveal || state.ready) {
    return;
  }

  const key = keyFor(row, col);
  if (!state.selected.has(key)) {
    return;
  }

  if (state.areaDraft.has(key)) {
    state.areaDraft.delete(key);
  } else {
    state.areaDraft.add(key);
  }

  updateCellVisualByKey(key);
}

function applyDragToAreaCell(key) {
  if (state.drag.visited.has(key)) {
    return;
  }
  state.drag.visited.add(key);

  const shouldAdd = state.drag.mode === "add";
  const inDraft = state.areaDraft.has(key);
  if (inDraft === shouldAdd) {
    return;
  }

  if (shouldAdd) {
    state.areaDraft.add(key);
  } else {
    state.areaDraft.delete(key);
  }
  updateCellVisualByKey(key);
}

function stopDrag() {
  state.drag.active = false;
  state.drag.visited.clear();
}

function askRuleNumber(rule) {
  let question = "";
  if (rule === "greater-than") {
    question = "Enter number for > n";
  } else if (rule === "less-than") {
    question = "Enter number for < n";
  } else {
    question = "Enter number for sum = n";
  }

  const input = window.prompt(question, "5");
  if (input === null) {
    return null;
  }

  const value = Number.parseInt(input, 10);
  if (Number.isNaN(value)) {
    boardHintEl.textContent = "Please enter a valid number.";
    return null;
  }

  return value;
}

function createArea(rule) {
  if (!state.reveal || state.ready) {
    boardHintEl.textContent = "Switch to selected board view first.";
    return;
  }

  if (state.areaDraft.size < 1) {
    boardHintEl.textContent = "Select at least one square to define an area.";
    return;
  }

  const needsNumber = rule === "greater-than" || rule === "less-than" || rule === "sum-equals";
  const parsedNumber = needsNumber ? askRuleNumber(rule) : null;
  if (needsNumber && parsedNumber === null) {
    return;
  }

  const id = state.nextAreaId;
  const cells = Array.from(state.areaDraft);
  const color = AREA_PALETTE[(id - 1) % AREA_PALETTE.length];
  const area = {
    id,
    rule,
    value: needsNumber ? parsedNumber : null,
    cells,
    color,
    anchor: cells[0],
  };

  cells.forEach((key) => {
    removeCellFromArea(key);
    state.cellArea.set(key, id);
  });

  state.areas.push(area);
  state.nextAreaId += 1;
  state.areaDraft.clear();
  boardHintEl.textContent = `${formatAreaRule(area)} created.`;

  refreshAllCells();
  renderAreasList();
}

function buildBoardGrid() {
  boardEl.innerHTML = "";
  cellEls.clear();
  boardEl.style.gridTemplateColumns = `repeat(${state.cols}, var(--cell-size))`;

  for (let row = 0; row < state.rows; row += 1) {
    for (let col = 0; col < state.cols; col += 1) {
      const key = keyFor(row, col);
      const cell = document.createElement("button");

      cell.type = "button";
      cell.className = "cell";
      cell.style.animationDelay = `${(row * state.cols + col) * 7}ms`;
      cell.setAttribute("role", "gridcell");
      cell.setAttribute("aria-label", `Row ${row + 1}, Column ${col + 1}`);
      cell.setAttribute("aria-pressed", "false");

      cell.addEventListener("mousedown", (event) => {
        event.preventDefault();
        if (event.button !== 0 || state.ready) {
          return;
        }

        if (state.reveal) {
          const inDraft = state.areaDraft.has(key);
          state.drag.active = true;
          state.drag.mode = inDraft ? "remove" : "add";
          state.drag.visited.clear();
          applyDragToAreaCell(key);
        } else {
          const selected = state.selected.has(key);
          state.drag.active = true;
          state.drag.mode = selected ? "remove" : "add";
          state.drag.visited.clear();
          setCellSelectionByKey(key, state.drag.mode === "add");
          updateCellVisualByKey(key);
          renderAreasList();
        }
      });

      cell.addEventListener("mouseenter", (event) => {
        if (state.ready || !state.drag.active) {
          return;
        }
        if ((event.buttons & 1) !== 1) {
          stopDrag();
          return;
        }

        if (state.reveal) {
          if (!state.selected.has(key)) {
            return;
          }
          applyDragToAreaCell(key);
        } else {
          if (state.drag.visited.has(key)) {
            return;
          }
          state.drag.visited.add(key);
          const shouldSelect = state.drag.mode === "add";
          const alreadySelected = state.selected.has(key);
          if (alreadySelected === shouldSelect) {
            return;
          }
          setCellSelectionByKey(key, shouldSelect);
          updateCellVisualByKey(key);
          renderAreasList();
        }
      });

      cellEls.set(key, cell);
      boardEl.appendChild(cell);
    }
  }

  refreshAllCells();
  renderAreasList();
  updateBoardModeUi();
}

function rebuildGrid() {
  const nextRows = clamp(Number.parseInt(rowsInput.value, 10) || 10, 2, 30);
  const nextCols = clamp(Number.parseInt(colsInput.value, 10) || 10, 2, 30);

  state.rows = nextRows;
  state.cols = nextCols;
  state.reveal = false;
  state.selected.clear();
  state.areaDraft.clear();
  state.areas = [];
  state.cellArea.clear();
  state.nextAreaId = 1;
  stopDrag();

  rowsInput.value = String(nextRows);
  colsInput.value = String(nextCols);

  buildBoardGrid();
}

function dominoKeys() {
  const keys = [];
  for (let left = 0; left <= 6; left += 1) {
    for (let right = left; right <= 6; right += 1) {
      keys.push(`${left}-${right}`);
    }
  }
  return keys;
}

function buildDominoPalette() {
  dominoesEl.innerHTML = "";
  const keys = state.ready ? dominoKeys().filter((key) => state.selectedDominoes.has(key)) : dominoKeys();

  if (keys.length === 0) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = "No dominoes selected.";
    dominoesEl.appendChild(empty);
    return;
  }

  keys.forEach((key) => {
    const [left, right] = key.split("-");
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "domino";
    tile.textContent = `${left} | ${right}`;
    const selected = state.selectedDominoes.has(key);
    if (selected) {
      tile.classList.add("selected");
    }
    tile.setAttribute("aria-pressed", selected ? "true" : "false");

    if (!state.ready) {
      tile.addEventListener("click", () => {
        if (state.selectedDominoes.has(key)) {
          state.selectedDominoes.delete(key);
          tile.classList.remove("selected");
          tile.setAttribute("aria-pressed", "false");
        } else {
          state.selectedDominoes.add(key);
          tile.classList.add("selected");
          tile.setAttribute("aria-pressed", "true");
        }
      });
    } else {
      tile.disabled = true;
    }

    dominoesEl.appendChild(tile);
  });
}

rebuildBtn.addEventListener("click", rebuildGrid);
toggleRevealBtn.addEventListener("click", () => {
  if (state.ready) {
    return;
  }
  state.reveal = !state.reveal;
  if (!state.reveal) {
    state.areaDraft.clear();
    refreshAllCells();
  }
  updateBoardModeUi();
});

function exportBoardAsJson() {
  const selected = Array.from(state.selected).map((key) => {
    const [r, c] = key.split(":").map(Number);
    return [r, c];
  });

  const areas = state.areas.map((area) => {
    const cells = area.cells.map((key) => {
      const [r, c] = key.split(":").map(Number);
      return [r, c];
    });
    return {
      rule: area.rule,
      value: area.value,
      cells,
    };
  });

  const dominoes = Array.from(state.selectedDominoes).map((key) => {
    const [left, right] = key.split("-").map(Number);
    return [left, right];
  });

  const board = {
    rows: state.rows,
    cols: state.cols,
    selected,
    areas,
    dominoes,
  };

  return board;
}

function downloadBoardJson() {
  const board = exportBoardAsJson();
  const json = JSON.stringify(board, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `pips-board-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

async function saveBoardJsonToServer() {
  const board = exportBoardAsJson();
  const response = await fetch(getApiUrl("/api/save-board"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(board),
  });

  const data = await response.json();
  if (!response.ok || data.status !== "saved") {
    throw new Error(data.error || "Failed to save board JSON");
  }

  return data;
}

readyBtn.addEventListener("click", async () => {
  state.ready = !state.ready;
  if (state.ready) {
    state.reveal = true;
    state.areaDraft.clear();
    stopDrag();
    try {
      const saved = await saveBoardJsonToServer();
      solveStatus.textContent = `Board saved to ${saved.path}`;
    } catch (error) {
      solveStatus.textContent = `Save failed: ${error.message}`;
    }
    downloadBoardJson();
    await solveBoardInBackground();
  } else {
    stopProcessPlayback();
  }
  updateBoardModeUi();
  refreshAllCells();
  buildDominoPalette();
});

playBackBtn.addEventListener("click", () => {
  state.ready = false;
  stopProcessPlayback();
  stopDrag();
  updateBoardModeUi();
  refreshAllCells();
  clearBoardLabels();
  boardEl.classList.remove("solved");
  buildDominoPalette();
});

clearBtn.addEventListener("click", () => {
  state.selected.clear();
  state.selectedDominoes.clear();
  state.reveal = false;
  state.ready = false;
  state.areaDraft.clear();
  state.areas = [];
  state.cellArea.clear();
  state.nextAreaId = 1;
  state.solveData = null;
  state.hintedSteps = 0;
  stopProcessPlayback();
  stopDrag();
  refreshAllCells();
  clearBoardLabels();
  boardEl.classList.remove("solved");
  renderAreasList();
  updateBoardModeUi();
  buildDominoPalette();
  setPlayButtonsDisabled(true);
  solveStatus.textContent = "";
});

ruleButtons.forEach((button) => {
  button.addEventListener("click", () => {
    createArea(button.dataset.rule);
  });
});

window.addEventListener("mouseup", () => {
  stopDrag();
});

// Export functions for testing
window.exportBoardAsJson = exportBoardAsJson;

hintBtn.addEventListener("click", () => {
  const steps = getSolveSteps();
  if (steps.length < 1) {
    solveStatus.textContent = "No solved steps available.";
    return;
  }

  stopProcessPlayback();
  state.hintedSteps = clamp(state.hintedSteps + 1, 0, steps.length);
  renderSolvedSteps(state.hintedSteps);
  solveStatus.textContent = `Hint: revealed ${state.hintedSteps}/${steps.length} piece(s).`;
});

solutionBtn.addEventListener("click", () => {
  const steps = getSolveSteps();
  if (steps.length < 1) {
    solveStatus.textContent = "No solved steps available.";
    return;
  }

  stopProcessPlayback();
  state.hintedSteps = steps.length;
  renderSolvedSteps(state.hintedSteps);
  solveStatus.textContent = "Full solution shown.";
});

processBtn.addEventListener("click", () => {
  const attempts = getProcessAttempts();
  const finalPlacements = getFinalPlacementSet();
  if (attempts.length < 1 || finalPlacements.size < 1) {
    solveStatus.textContent = "No process attempts available.";
    return;
  }

  stopProcessPlayback();
  state.hintedSteps = 0;
  const runId = state.processRunId;
  const fixedValues = new Map();
  renderFixedValueMap(fixedValues);
  solveStatus.textContent = "Showing solution process (wrong attempts included)...";

  const playAttemptAt = (index) => {
    if (runId !== state.processRunId) {
      return;
    }

    if (index >= attempts.length) {
      renderFixedValueMap(fixedValues);
      solveStatus.textContent = "Solution process complete.";
      return;
    }

    const attempt = attempts[index];
    const [v1, v2] = attempt.values;
    const signature = placementSignature(attempt.cell, attempt.neighbor, v1, v2);
    const isFinalPlacement = finalPlacements.has(signature);

    renderFixedValueMap(fixedValues);
    paintAttempt(attempt, !isFinalPlacement);

    state.processTimer = window.setTimeout(() => {
      if (runId !== state.processRunId) {
        return;
      }

      if (isFinalPlacement) {
        const [r1, c1] = attempt.cell;
        const [r2, c2] = attempt.neighbor;
        fixedValues.set(keyFor(r1, c1), v1);
        fixedValues.set(keyFor(r2, c2), v2);
      }

      renderFixedValueMap(fixedValues);
      state.processTimer = window.setTimeout(() => {
        playAttemptAt(index + 1);
      }, 45);
    }, isFinalPlacement ? 140 : 90);
  };

  playAttemptAt(0);
});

statsBtn.addEventListener("click", () => {
  showSearchStats();
});

buildBoardGrid();
buildDominoPalette();
setPlayButtonsDisabled(true);
