/* Meshubatzim – client logic: view toggle, click-to-edit, realtime. */
(function () {
  "use strict";
  var pageClientId = Date.now().toString(36) + Math.random().toString(36).slice(2);
  var saveStates = new WeakMap();

  function init() {
    var board = document.getElementById("board");
    if (!board) return;
    setupViewToggle(board);
    setupClickEdit();
    setupAutosave();
    setupRecurringModal();
    setupRealtime(board.dataset.week);
  }

  /* ---------- Table <-> Cards toggle ---------- */
  function setupViewToggle(board) {
    var btn = document.getElementById("view-toggle");
    var KEY = "meshubatzim:view";

    function apply(view) {
      board.classList.toggle("show-cards", view === "cards");
      if (btn) btn.setAttribute("aria-pressed", view === "cards" ? "true" : "false");
    }

    var saved = localStorage.getItem(KEY);
    if (!saved) {
      saved = window.matchMedia("(max-width: 720px)").matches ? "cards" : "table";
    }
    apply(saved);

    if (btn) {
      btn.addEventListener("click", function () {
        var next = board.classList.contains("show-cards") ? "table" : "cards";
        localStorage.setItem(KEY, next);
        apply(next);
      });
    }
  }

  /* ---------- Click-to-edit (default view mode) ---------- */
  function enterEdit(cell) {
    if (cell.classList.contains("is-editing")) return;
    cell.classList.add("is-editing");
    var state = saveState(cell);
    if (!state.dirty && !state.saving) setSaveStatus(cell, "");
    var name = cell.querySelector(".cell-name");
    if (name) {
      name.focus();
      name.select();
    }
  }

  function exitEdit(cell) {
    if (!cell.classList.contains("is-editing")) return;
    cell.classList.remove("is-editing");
  }

  function saveState(cell) {
    if (!saveStates.has(cell)) {
      saveStates.set(cell, { revision: 0, dirty: false, saving: false, timer: null });
    }
    return saveStates.get(cell);
  }

  function setSaveStatus(cell, status) {
    var indicator = cell.querySelector(".cell-save-status");
    if (!indicator) return;
    var state = saveState(cell);
    clearTimeout(state.statusTimer);
    var close = cell.querySelector(".cell-close");
    if (close) close.hidden = status !== "";
    indicator.dataset.state = status;
    indicator.textContent = status === "saved" ? "✓" : status === "error" ? "!" : "";
    indicator.setAttribute("aria-label", status === "saving" ? "שומר שינויים" : status === "saved" ? "נשמר" : status === "error" ? "השמירה נכשלה. יש לנסות שוב" : "");
    cell.setAttribute("aria-busy", status === "saving" ? "true" : "false");
    if (status === "saved") {
      state.statusTimer = setTimeout(function () {
        if (!state.dirty && !state.saving) setSaveStatus(cell, "");
      }, 1600);
    }
  }

  async function saveCell(cell) {
    var state = saveState(cell);
    clearTimeout(state.timer);
    state.timer = null;
    if (!state.dirty || state.saving) return;
    var revision = state.revision;
    var form = cell.querySelector(".cell-form");
    state.saving = true;
    state.dirty = false;
    setSaveStatus(cell, "saving");
    try {
      var response = await fetch(form.action, {
        method: "POST",
        keepalive: true,
        headers: {
          "Accept": "application/json",
          "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content,
          "X-Client-ID": pageClientId
        },
        body: new FormData(form)
      });
      if (!response.ok) throw new Error("Save failed");
      var data = await response.json();
      if (state.revision === revision) {
        document.querySelectorAll(cellSelector(data)).forEach(function (other) {
          if (other === cell) renderCellData(other, data);
          else applyCellUpdate(other, data);
        });
        setSaveStatus(cell, "saved");
      }
    } catch (error) {
      if (state.revision === revision) {
        state.dirty = true;
        setSaveStatus(cell, "error");
      }
    } finally {
      state.saving = false;
      // Serialize saves so an older request cannot overwrite newer typing.
      if (state.dirty && state.revision !== revision && !state.timer) saveCell(cell);
    }
  }

  function setupAutosave() {
    document.addEventListener("input", function (event) {
      if (!event.target.matches(".cell-name, .cell-notes")) return;
      var cell = event.target.closest(".cell");
      var state = saveState(cell);
      state.revision++;
      clearTimeout(state.timer);
      state.timer = null;
      if (!state.saving &&
          cell.querySelector(".cell-name").value.trim() === cell.querySelector(".cell-name-text").textContent.trim() &&
          cell.querySelector(".cell-notes").value.trim() === cell.querySelector(".cell-notes-text").textContent.trim()) {
        state.dirty = false;
        setSaveStatus(cell, "");
        return;
      }
      state.dirty = true;
      setSaveStatus(cell, "saving");
      state.timer = setTimeout(function () {
        state.timer = null;
        saveCell(cell);
      }, 600);
    });
    document.addEventListener("submit", function (event) {
      if (!event.target.matches(".cell-form")) return;
      event.preventDefault();
      saveCell(event.target.closest(".cell"));
    });
  }

  function setupClickEdit() {
    // Open the editor when an editable cell (in view mode) is clicked.
    document.addEventListener("click", function (e) {
      var close = e.target.closest(".cell-close");
      if (close) {
        var closingCell = close.closest(".cell");
        saveCell(closingCell);
        exitEdit(closingCell);
        closingCell.focus();
        return;
      }
      var cell = e.target.closest(".cell.editable");
      if (cell && !cell.classList.contains("is-editing")) enterEdit(cell);
    });

    // Keyboard: Enter/Space opens; Escape closes and saves pending changes.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        var editing = e.target.closest(".cell.is-editing");
        if (editing) {
          saveCell(editing);
          exitEdit(editing);
        }
        return;
      }
      if (e.key === "Enter" || e.key === " ") {
        var cell = e.target.closest(".cell.editable");
        if (cell && cell === e.target && !cell.classList.contains("is-editing")) {
          e.preventDefault();
          enterEdit(cell);
        }
      }
    });

    // Leaving a cell flushes pending changes instead of discarding them.
    document.addEventListener("focusout", function (e) {
      var cell = e.target.closest(".cell.is-editing");
      if (!cell) return;
      setTimeout(function () {
        var active = document.activeElement;
        if (cell.contains(active)) return;
        if (active && active.closest && active.closest("#recurring-modal")) return;
        saveCell(cell);
        exitEdit(cell);
      }, 0);
    });
  }

  /* ---------- Recurring ("save as recurring") modal ---------- */
  function setupRecurringModal() {
    var modal = document.getElementById("recurring-modal");
    if (!modal) return;
    var untilInput = modal.querySelector("#rec-until");
    var foreverBadge = modal.querySelector("#rec-forever");
    var untilHint = modal.querySelector("#rec-until-hint");

    function updateEndDateLabel() {
      foreverBadge.hidden = Boolean(untilInput.value);
      untilHint.hidden = !untilInput.value;
    }
    untilInput.addEventListener("input", updateEndDateLabel);
    untilInput.addEventListener("change", updateEndDateLabel);
    updateEndDateLabel();

    function open(cell) {
      updateEndDateLabel();
      modal.querySelector("#rec-day").value = cell.dataset.day;
      modal.querySelector("#rec-shift").value = cell.dataset.shift;
      var name = cell.querySelector(".cell-name");
      var notes = cell.querySelector(".cell-notes");
      modal.querySelector("#rec-name").value = name ? name.value : "";
      modal.querySelector("#rec-notes").value = notes ? notes.value : "";
      modal.querySelector("#rec-cell-label").textContent =
        (cell.dataset.dayName || "") + " · " + (cell.dataset.shiftLabel || "");
      modal.hidden = false;
      document.body.classList.add("modal-open");
      var first = modal.querySelector("#rec-name");
      if (first) first.focus();
    }

    function close() {
      modal.hidden = true;
      document.body.classList.remove("modal-open");
    }

    document.addEventListener("click", function (e) {
      var pin = e.target.closest(".cell-recurring");
      if (pin) {
        e.preventDefault();
        var cell = pin.closest(".cell");
        if (cell) open(cell);
        return;
      }
      if (!modal.hidden && e.target.closest("[data-close]")) close();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !modal.hidden) close();
    });

    // Saved via HTMX (no page reload): close the modal + show a toast.
    document.body.addEventListener("recurring-saved", function () {
      close();
      showToast("נשמר כקבוע (חוזר) — יועתק אוטומטית ללוחות חדשים");
    });
  }

  /* ---------- Toast ---------- */
  function showToast(msg) {
    var t = document.createElement("div");
    t.className = "toast";
    t.setAttribute("role", "status");
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(function () { t.classList.add("show"); });
    setTimeout(function () {
      t.classList.remove("show");
      setTimeout(function () { t.remove(); }, 300);
    }, 3200);
  }

  /* ---------- Realtime (Socket.IO) ---------- */
  function setupRealtime(week) {
    if (typeof io === "undefined" || !week) return;
    var groupId = new URLSearchParams(window.location.search).get("groupId");
    var socket = io({ query: { groupId: groupId } });
    var hasConnected = false;

    socket.on("connect", function () {
      if (hasConnected) {
        window.location.reload();
        return;
      }
      hasConnected = true;
      socket.emit("join", { week: week });
    });
    socket.on("presence", function (data) {
      updatePresence(data && data.count);
    });
    socket.on("slot_updated", function (data) {
      if (data && data.week === week) applyRemoteUpdate(data);
    });
  }

  function updatePresence(count) {
    var el = document.getElementById("presence");
    if (!el) return;
    var others = Math.max(0, (count || 0) - 1);
    if (others > 0) {
      el.textContent = others === 1
        ? "משתמש נוסף מחובר"
        : others + " משתמשים נוספים מחוברים";
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  }

  function applyRemoteUpdate(data) {
    // Our own broadcast may arrive before the HTTP response; keep typing intact.
    if (data.client_id === pageClientId) return;
    document.querySelectorAll(cellSelector(data)).forEach(function (cell) {
      applyCellUpdate(cell, data);
    });
  }

  function cellSelector(data) {
    return '.cell[data-day="' + data.day_index + '"][data-shift="' + data.shift + '"]';
  }

  function applyCellUpdate(cell, data) {
    var state = saveState(cell);
    clearTimeout(state.timer);
    state.timer = null;
    state.revision++;
    state.dirty = false;
    exitEdit(cell);
    if (cell.contains(document.activeElement)) document.activeElement.blur();
    renderCellData(cell, data);
    setSaveStatus(cell, "");
    flash(cell);
  }

  function renderCellData(cell, data) {
    var nameInput = cell.querySelector(".cell-name");
    var notesInput = cell.querySelector(".cell-notes");
    if (nameInput) nameInput.value = data.assignee || "";
    if (notesInput) notesInput.value = data.notes || "";

    var nameText = cell.querySelector(".cell-name-text");
    var notesText = cell.querySelector(".cell-notes-text");
    if (nameText) nameText.textContent = data.assignee || "";
    if (notesText) notesText.textContent = data.notes || "";

    cell.classList.toggle("is-empty", !data.assignee);
  }

  function flash(el) {
    el.classList.remove("cell-flash");
    void el.offsetWidth; // restart the CSS animation
    el.classList.add("cell-flash");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
