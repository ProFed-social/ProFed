// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  function parts(form) {
    return {files: form.querySelector(".compose-files"),
            previews: form.querySelector(".compose-previews"),
            warning: form.querySelector(".compose-warning"),
            warn: form.querySelector(".compose-warn")};
  }

  function without(list, dropped) {
    var kept = new DataTransfer();
    Array.prototype.forEach.call(list, function (file) {
      if (file !== dropped) { kept.items.add(file); }
    });
    return kept.files;
  }

  function preview(file, onRemove) {
    var figure = document.createElement("figure");
    figure.className = "compose-preview";

    var image = document.createElement("img");
    image.src = URL.createObjectURL(file);
    image.alt = "";
    image.addEventListener("load", function () { URL.revokeObjectURL(image.src); });

    var alt = document.createElement("input");
    alt.type = "text";
    alt.name = "media_descriptions";
    alt.className = "compose-alt";
    alt.placeholder = "Describe this image";
    alt.setAttribute("aria-label", "Describe " + file.name);

    var remove = document.createElement("button");
    remove.type = "button";
    remove.className = "compose-preview-remove";
    remove.title = "Remove";
    remove.setAttribute("aria-label", "Remove " + file.name);
    remove.textContent = "×";
    remove.addEventListener("click", function () { onRemove(file); });

    figure.append(image, alt, remove);
    return figure;
  }

  function render(form) {
    var held = parts(form);

    function drop(file) {
      held.files.files = without(held.files.files, file);
      render(form);
    }

    held.previews.replaceChildren();
    Array.prototype.forEach.call(held.files.files, function (file) {
      held.previews.append(preview(file, drop));
    });
    held.previews.hidden = held.files.files.length === 0;
  }

  function nameLanguages() {
    var options = document.querySelectorAll("#compose-languages option");
    if (!window.Intl || !Intl.DisplayNames || !options.length) { return; }

    var names = new Intl.DisplayNames([navigator.language || "en"], {type: "language", fallback: "none"});
    options.forEach(function (option) {
      try {
        option.label = names.of(option.value) || option.label;
      } catch (notATag) {
        option.dataset.unnamed = "malformed";
      }
    });
  }

  function bind(form) {
    var held = parts(form);

    form.querySelector(".compose-attach").addEventListener("click", function () { held.files.click(); });
    held.files.addEventListener("change", function () { render(form); });
    held.warn.addEventListener("click", function () {
      held.warning.hidden = !held.warning.hidden;
      held.warn.setAttribute("aria-pressed", String(!held.warning.hidden));
      if (!held.warning.hidden) { held.warning.focus(); }
    });
    form.addEventListener("compose:reset", function () {
      held.warning.hidden = true;
      held.warn.setAttribute("aria-pressed", "false");
      render(form);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector(".compose-dialog .compose");
    if (!form) { return; }
    bind(form);
    nameLanguages();
  });
})();

