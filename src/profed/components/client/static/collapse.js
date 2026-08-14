// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later
 
(function () {
  function measure(root) {
    root.querySelectorAll(".e-content.not-expandable, .thread-body.not-expandable").forEach(function (content) {
      var max = parseFloat(getComputedStyle(content).maxHeight);
      var overflows = isNaN(max)
        ? content.scrollHeight - content.clientHeight > 2
        : content.scrollHeight > max + 2;
      if (overflows) { 
        content.classList.replace("not-expandable", "expandable");
      }
    });
    root.querySelectorAll(".show-more").forEach(function (more) {
      more.addEventListener("click", function () {
        more.parentElement.querySelector(".thread-body, .e-content").classList.replace("expandable", "collapsable");
      });
    });
    root.querySelectorAll(".show-less").forEach(function (less) {
      less.addEventListener("click", function () {
        less.parentElement.querySelector(".thread-body, .e-content").classList.replace("collapsable", "expandable");
      });
    });
  }
 
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { measure(document); });
  } else {
    document.addEventListener("DOMContentLoaded", function () { measure(document); });
  }
  document.addEventListener("htmx:afterSwap", function (event) { measure(event.target); });
})();

