// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later
 
(function () {
  function compose() {
    return document.querySelector(".compose");
  }
 
  function clearTarget(form) {
    form.querySelector("[name=in_reply_to_id]").value = "";
    form.querySelector(".compose-reply-target").hidden = true;
  }
 
  function bindTriggers(root) {
    root.querySelectorAll(".reply-trigger").forEach(function (button) {
      button.addEventListener("click", function () {
        var form = compose();
        if (!form) { return; }
        form.querySelector("[name=in_reply_to_id]").value = button.dataset.replyId;
        form.querySelector(".compose-reply-target-name").textContent = button.dataset.replyName;
        form.querySelector(".compose-reply-target-text").textContent = button.dataset.replyText;
        form.querySelector(".compose-reply-target").hidden = false;
        form.querySelector("textarea").focus();
        form.scrollIntoView({behavior: "smooth", block: "nearest"});
      });
    });
  }
 
  function bindCompose() {
    var form = compose();
    if (!form) { return; }
    form.querySelector(".compose-reply-clear").addEventListener("click", function () { clearTarget(form); });
    form.addEventListener("htmx:afterRequest", function (event) {
      if (event.detail.successful) { form.reset(); clearTarget(form); }
    });
  }
 
  document.addEventListener("DOMContentLoaded", function () { bindTriggers(document); bindCompose(); });
  document.addEventListener("htmx:afterSwap", function (event) { bindTriggers(event.target); });
})();

