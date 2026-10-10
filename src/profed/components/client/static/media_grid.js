// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  function relayoutAll(root) {
    function relayout(wrapper) {
      function countFrom(value, fallback) {
        var parsed = parseInt(value, 10);
        return parsed > 0 ? parsed : fallback;
      }

      function reflow(grid, fill) {
        function ratioOf(item) {
          return parseFloat(item.style.getPropertyValue("--ratio")) || 1;
        }

        function emptyRow() {
          var row = document.createElement("div");
          row.className = "media-row";
          grid.appendChild(row);
          return row;
        }

        var items = Array.prototype.slice.call(grid.querySelectorAll(".media-item"));
        if ( !items.length ) { return; }

        grid.innerHTML = "";
        var rows = [];
        var filled = fill;

        items.forEach(function (item) {
          if ( filled >= fill ) {
            rows.push(emptyRow());
            filled = 0;
          }
          var row = rows[rows.length - 1];
          row.appendChild(item);
          filled += ratioOf(item);
          if ( filled >= fill ) { row.classList.add("fills"); }
        });
      }

      function trim(budget) {
        function units() {
          return Array.prototype.slice.call(wrapper.children).reduce(function (collected, child) {
            if ( child.matches(".media-grid") ) {
              return collected.concat(Array.prototype.slice.call(child.children));
            }
            return child.matches(".media-block") ? collected.concat([child]) : collected;
          }, []);
        }

        units().slice(budget).forEach(function (unit) { unit.remove(); });
        wrapper.querySelectorAll(".media-grid").forEach(function (grid) {
          if ( !grid.children.length ) { grid.remove(); }
        });
      }

      function shown() {
        return wrapper.querySelectorAll(".media-item, .media-block").length;
      }

      function mark(badge, missing) {
        if ( missing <= 0 ) {
          if ( badge ) { badge.remove(); }
          return;
        }
        var span = badge || document.createElement("span");
        span.className = "media-more";
        span.textContent = "+" + missing;
        wrapper.appendChild(span);
      }

      var badge = wrapper.querySelector(".media-more");
      var width = wrapper.clientWidth;
      var maxHeight = parseFloat(getComputedStyle(wrapper).getPropertyValue("--media-max-height"));
      if ( !width || !maxHeight ) { return; }

      if (badge) { badge.remove(); }

      var fill = width / maxHeight;
      wrapper.querySelectorAll(".media-grid").forEach(function (grid) { reflow(grid, fill); });

      trim(countFrom(wrapper.dataset.mediaBudget, Infinity));
      mark(badge, countFrom(wrapper.dataset.mediaTotal, shown()) - shown());
    }

    root.querySelectorAll("[data-media]").forEach(relayout);
  }

  var pending = null;

  document.addEventListener("DOMContentLoaded", function () { relayoutAll(document); });
  document.addEventListener("htmx:afterSwap", function (event) { relayoutAll(event.target); });
  window.addEventListener("resize", function () {
    if ( pending ) { return; }
    pending = window.requestAnimationFrame(function () {
      pending = null;
      relayoutAll(document);
    });
  });
})();

