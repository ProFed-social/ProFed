// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  function compose() {
    return document.querySelector(".conversation-compose");
  }

  function clearTarget(form) {
    form.querySelector("[name=in_reply_to_id]").value = "";
    form.querySelector(".conversation-reply-target").hidden = true;
  }

  function scrollToBottom() {
    var list = document.querySelector(".conversation-messages");
    if (list) { list.scrollTop = list.scrollHeight; }
  }

  function bindReplyButtons(root) {
    root.querySelectorAll(".msg-reply-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        var form = compose();
        if (!form) { return; }
        form.querySelector("[name=in_reply_to_id]").value = button.dataset.replyId;
        form.querySelector(".conversation-reply-target-name").textContent = button.dataset.replyName;
        form.querySelector(".conversation-reply-target-text").textContent = button.dataset.replyText;
        form.querySelector(".conversation-reply-target").hidden = false;
        form.querySelector(".conversation-input").focus();
      });
    });
  }

  function bindCompose() {
    var form = compose();
    if (!form) { return; }
    form.querySelector(".conversation-reply-clear").addEventListener("click", function () { clearTarget(form); });
    form.querySelector(".conversation-input").addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
    form.addEventListener("htmx:afterRequest", function (event) {
      if (event.detail.successful) { form.reset(); clearTarget(form); }
    });
  }

  document.addEventListener("DOMContentLoaded", function () { bindReplyButtons(document); bindCompose(); scrollToBottom(); });
  document.addEventListener("htmx:afterSwap", function (event) { bindReplyButtons(event.target); scrollToBottom(); });
})();

