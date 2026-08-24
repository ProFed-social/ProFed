// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  function closeAll(except) {
    document.querySelectorAll("details.action-menu[open]").forEach(function (menu) {
      if (menu !== except) { menu.open = false; }
    });
  }

  document.addEventListener("click", function (event) {
    closeAll(event.target.closest("details.action-menu"));
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") { closeAll(null); }
  });
})();

