// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  function ratioOf(item) {
    return parseFloat(item.style.getPropertyValue("--ratio")) || 1;
  }

  function countFrom(value, fallback) {
    var parsed = parseInt(value, 10);
    return parsed > 0 ? parsed : fallback;
  }

  function emptyRow(grid) {
    var row = document.createElement("div");
    row.className = "media-row";
    grid.appendChild(row);
    return row;
  }

  function rowsFor(grid, items, fill) {
    var rows = [];
    var filled = fill;

    items.forEach(function (item) {
      if (filled >= fill) {
        rows.push(emptyRow(grid));
        filled = 0;
      }
      var row = rows[rows.length - 1];
      row.appendChild(item);
      filled += ratioOf(item);
      if (filled >= fill) { row.classList.add("fills"); }
    });

    return rows;
  }

  function mark(grid, badge, missing) {
    if (missing <= 0) { return; }
    var span = badge || document.createElement("span");
    span.className = "media-more";
    span.textContent = "+" + missing;
    grid.lastElementChild.appendChild(span);
  }

  function relayout(grid) {
    var items = Array.prototype.slice.call(grid.querySelectorAll(".media-item"));
    var badge = grid.querySelector(".media-more");
    var width = grid.clientWidth;
    var maxHeight = parseFloat(getComputedStyle(grid).getPropertyValue("--media-max-height"));
    if (!items.length || !width || !maxHeight) { return; }

    var fill = width / maxHeight;
    var limit = countFrom(grid.dataset.mediaRows, Infinity);
    var total = countFrom(grid.dataset.mediaTotal, items.length);

    grid.innerHTML = "";
    var rows = rowsFor(grid, items, fill);
    while (rows.length > limit) { grid.removeChild(rows.pop()); }
    mark(grid, badge, total - grid.querySelectorAll(".media-item").length);
  }

  function relayoutAll(root) {
    root.querySelectorAll("[data-media-grid]").forEach(relayout);
  }

  var pending = null;
  function schedule() {
    if (pending) { return; }
    pending = window.requestAnimationFrame(function () {
      pending = null;
      relayoutAll(document);
    });
  }

  document.addEventListener("DOMContentLoaded", function () { relayoutAll(document); });
  document.addEventListener("htmx:afterSwap", function (event) { relayoutAll(event.target); });
  window.addEventListener("resize", schedule);
})();

