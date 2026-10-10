// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  var SLOTS = {image: ".media-viewer-image",
               video: ".media-viewer-video",
               document: ".media-viewer-frame"};

  function clear(dialog) {
    Object.keys(SLOTS).forEach(function (kind) {
      var slot = dialog.querySelector(SLOTS[kind]);
      if ( !slot ) { return; }

      if ( slot.tagName === "VIDEO" ) { slot.pause(); }
      slot.removeAttribute("src");
      slot.hidden = true;
    });
  }

  document.addEventListener("click", function (event) {
    function viewer() {
      return document.querySelector("[data-media-viewer]");
    }

    function open(url, kind) {
      var dialog = viewer();
      var slot = dialog && dialog.querySelector(SLOTS[kind] || "");
      if ( !dialog || !slot || !url ) { return; }

      clear(dialog);
      slot.setAttribute("src", url);
      slot.hidden = false;
      dialog.showModal();
      if ( slot.tagName === "VIDEO" ) { slot.play().catch(function () {}); }
    }

    function close() {
      var dialog = viewer();
      if ( !dialog ) { return; }

      clear(dialog);
      if ( dialog.open ) { dialog.close(); }
    }

    var trigger = event.target.closest("[data-media-open]");
    if ( trigger ) {
      event.preventDefault();
      open(trigger.dataset.mediaOpen, trigger.dataset.mediaKind);
      return;
    }

    if ( event.target.closest("[data-media-viewer-close]") ) {
      close();
    }
  });

  document.addEventListener("close", function (event) {
    if ( event.target.matches("[data-media-viewer]") ) { clear(event.target); }
  }, true);
})();

