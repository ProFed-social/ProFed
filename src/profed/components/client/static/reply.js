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

  function messages() {
    return document.querySelector(".conversation-messages");
  }

  function scrollToBottom() {
    var list = messages();
    if (list) { list.scrollTop = list.scrollHeight; }
  }

  function requestedPath(event) {
    return (event.detail && event.detail.requestConfig && event.detail.requestConfig.path) || "";
  }
 
  function loadsOlderMessages(event) {
    return requestedPath(event).indexOf("/messages/more") !== -1;
  }
 
  function sendsAReply(event) {
    return /\/conversations\/[^/]+\/reply$/.test(requestedPath(event));
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

  var heightBeforeSwap = null;

  document.addEventListener("DOMContentLoaded", function () { bindReplyButtons(document); bindCompose(); scrollToBottom(); });
  document.addEventListener("htmx:beforeSwap", function (event) {
    var list = messages();
    heightBeforeSwap = loadsOlderMessages(event) && list ? list.scrollHeight : null;
  });
 
  document.addEventListener("htmx:afterSwap", function (event) {
    var list = messages();
    bindReplyButtons(event.target);
    if (heightBeforeSwap !== null && list) {
      list.scrollTop += list.scrollHeight - heightBeforeSwap;
      heightBeforeSwap = null;
    } else if (sendsAReply(event)) {
      scrollToBottom();
    }
})();

