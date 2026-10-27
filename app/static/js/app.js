/* Meshubatzim – client logic: view toggle, click-to-edit, realtime. */
(function () {
  "use strict";

  function init() {
    var board = document.getElementById("board");
    if (!board) return;
    setupViewToggle(board);
    setupClickEdit();
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
    var name = cell.querySelector(".cell-name");
    if (name) {
      name.focus();
      name.select();
    }
  }

  function exitEdit(cell, revert) {
    if (!cell.classList.contains("is-editing")) return;
    cell.classList.remove("is-editing");
    if (revert) {
      var name = cell.querySelector(".cell-name");
      var notes = cell.querySelector(".cell-notes");
      var nameText = cell.querySelector(".cell-name-text");
      var notesText = cell.querySelector(".cell-notes-text");
      if (name && nameText) name.value = nameText.textContent.trim();
      if (notes && notesText) notes.value = notesText.textContent.trim();
    }
  }

  function setupClickEdit() {
    // Open the editor when an editable cell (in view mode) is clicked.
    document.addEventListener("click", function (e) {
      var cancel = e.target.closest(".cell-cancel");
      if (cancel) {
        var editingCell = cancel.closest(".cell");
        if (editingCell) exitEdit(editingCell, true);
        return;
      }
      var cell = e.target.closest(".cell.editable");
      if (cell && !cell.classList.contains("is-editing")) enterEdit(cell);
    });

    // Keyboard: Enter/Space opens; Escape cancels.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        var editing = e.target.closest(".cell.is-editing");
        if (editing) exitEdit(editing, true);
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

    // Click/focus away from an editing cell cancels (discards unsaved input),
    // unless focus moved into the recurring modal (keep the edit alive behind it).
    document.addEventListener("focusout", function (e) {
      var cell = e.target.closest(".cell.is-editing");
      if (!cell) return;
      setTimeout(function () {
        var active = document.activeElement;
        if (cell.contains(active)) return;
        if (active && active.closest && active.closest("#recurring-modal")) return;
        exitEdit(cell, true);
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
      var pin = e.target.closest(".cell-pin");
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
    var selector = '.cell[data-day="' + data.day_index + '"][data-shift="' + data.shift + '"]';
    document.querySelectorAll(selector).forEach(function (cell) {
      // Incoming state replaces the draft and returns the cell to view mode.
      exitEdit(cell, false);
      if (cell.contains(document.activeElement)) document.activeElement.blur();

      var nameInput = cell.querySelector(".cell-name");
      var notesInput = cell.querySelector(".cell-notes");
      if (nameInput) nameInput.value = data.assignee || "";
      if (notesInput) notesInput.value = data.notes || "";

      var nameText = cell.querySelector(".cell-name-text");
      var notesText = cell.querySelector(".cell-notes-text");
      if (nameText) nameText.textContent = data.assignee || "";
      if (notesText) notesText.textContent = data.notes || "";

      cell.classList.toggle("is-empty", !data.assignee);
      flash(cell);
    });
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
