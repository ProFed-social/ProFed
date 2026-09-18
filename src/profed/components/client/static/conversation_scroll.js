// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later
 
(function () {
  var PANE = "conversation-messages";
  var heightBeforeSwap = null;
 
  function pane() {
    return document.getElementById(PANE);
  }
 
  function toTheNewest(messages) {
    if (messages) {
      messages.scrollTop = messages.scrollHeight;
    }
  }
 
  function loadsOlderMessages(target) {
    return target && target.classList && target.classList.contains("more--older");
  }
 
  document.addEventListener("DOMContentLoaded", function () { toTheNewest(pane()); });
 
  document.addEventListener("htmx:beforeSwap", function (event) {
    var messages = pane();
    heightBeforeSwap = loadsOlderMessages(event.target) && messages ? messages.scrollHeight : null;
  });
 
  document.addEventListener("htmx:afterSwap", function (event) {
    var messages = pane();
    if (!messages) {
      return;
    }
    if (heightBeforeSwap !== null) {
      messages.scrollTop += messages.scrollHeight - heightBeforeSwap;
      heightBeforeSwap = null;
    } else if (event.target === messages || messages.contains(event.target)) {
      toTheNewest(messages);
    }
  });
})();

