// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later
 
(function () {
  var PANE = "conversation-messages";
  var heightBeforeSwap = null;
 
  function pane() {
    return document.getElementById(PANE);
  }
 
  function toTheNewest() {
    var messages = pane();
    if (messages) {
      messages.scrollTop = messages.scrollHeight;
    }
  }
 
  function requestedPath(event) {
    return (event.detail && event.detail.requestConfig && event.detail.requestConfig.path) || "";
  }
 
  function loadsOlderMessages(event) {
    return requestedPath(event).indexOf("/messages/more") !== -1;
  }
 
  function replacesTheWholePane(event) {
    return /\/conversations\/[^/]+\/reply$/.test(requestedPath(event));
  }
 
  document.addEventListener("DOMContentLoaded", toTheNewest);
 
  document.addEventListener("htmx:beforeSwap", function (event) {
    var messages = pane();
    heightBeforeSwap = loadsOlderMessages(event) && messages ? messages.scrollHeight : null;
  });
 
  document.addEventListener("htmx:afterSwap", function (event) {
    var messages = pane();
    if (heightBeforeSwap !== null && messages) {
      messages.scrollTop += messages.scrollHeight - heightBeforeSwap;
      heightBeforeSwap = null;
    } else if (replacesTheWholePane(event)) {
      toTheNewest();
    }
  });
})();

