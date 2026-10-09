// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  function dialog() {
    return document.querySelector(".compose-dialog");
  }

  function compose() {
    var box = dialog();
    return box && box.querySelector(".compose");
  }

  function clearTarget(form) {
    form.querySelector("[name=in_reply_to_id]").value = "";
    form.querySelector(".compose-reply-target").hidden = true;
    form.querySelector(".compose-heading").textContent = "New post";
  }

  function open(form) {
    dialog().showModal();
    form.querySelector("textarea").focus();
  }

  function replyTo(form, button) {
    form.querySelector("[name=in_reply_to_id]").value = button.dataset.replyId;
    form.querySelector(".compose-reply-target-name").textContent = button.dataset.replyName;
    form.querySelector(".compose-reply-target-text").textContent = button.dataset.replyText;
    form.querySelector(".compose-reply-target").hidden = false;
    form.querySelector(".compose-heading").textContent = "Reply";
  }

  function bindTriggers(root) {
    root.querySelectorAll(".reply-trigger").forEach(function (button) {
      button.addEventListener("click", function () {
        var form = compose();
        if (!form) { return; }
        replyTo(form, button);
        open(form);
      });
    });
  }

  function show(markup) {
    var posts = document.querySelector(".posts");
    if (!posts) { return; }

    var before = Array.prototype.slice.call(posts.children);
    posts.insertAdjacentHTML("afterbegin", markup);
    Array.prototype.forEach.call(posts.children, function (child) {
      if (before.indexOf(child) !== -1) { return; }
      if (window.htmx) { window.htmx.process(child); }
      bindTriggers(child);
    });
  }

  function done(form) {
    form.reset();
    clearTarget(form);
    form.dispatchEvent(new CustomEvent("compose:reset"));
    dialog().close();
  }

  function bindCompose() {
    var form = compose();
    if (!form) { return; }
    document.querySelector(".compose-open").addEventListener("click", function () {
      clearTarget(form);
      open(form);
    });
    form.querySelector(".compose-close").addEventListener("click", function () { dialog().close(); });
    form.querySelector(".compose-reply-clear").addEventListener("click", function () { clearTarget(form); });
    form.addEventListener("htmx:afterRequest", function (event) {
      if (!event.detail.successful) { return; }
      show(event.detail.xhr.responseText);
      done(form);
    });
  }

  document.addEventListener("DOMContentLoaded", function () { bindTriggers(document); bindCompose(); });
  document.addEventListener("htmx:afterSwap", function (event) { bindTriggers(event.target); });
})();

