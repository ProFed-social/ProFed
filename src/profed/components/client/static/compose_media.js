// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  function parts(form) {
    return {files: form.querySelector(".compose-files"),
            previews: form.querySelector(".compose-previews"),
            warning: form.querySelector(".compose-warning"),
            warn: form.querySelector(".compose-warn")};
  }

  function render(form) {
    var held = parts(form);

    function without(list, dropped) {
      var kept = new DataTransfer();
      Array.prototype.forEach.call(list, function (file) {
        if ( file !== dropped ) { kept.items.add(file); }
      });
      return kept.files;
    }

    function drop(file) {
      held.files.files = without(held.files.files, file);
      render(form);
    }

    function preview(file) {
      function flavourOf(file) {
        var type = file.type || "";
        return type.indexOf("image/") === 0 ? "image"
             : type.indexOf("video/") === 0 ? "video"
             : type.indexOf("audio/") === 0 ? "audio"
                                            : "file";
      }

      function thumbnail(file, flavour) {
        function revoking(element, event) {
          element.src = URL.createObjectURL(file);
          element.addEventListener(event, function () { URL.revokeObjectURL(element.src); });
          return element;
        }

        if ( flavour === "image" ) {
          var image = revoking(document.createElement("img"), "load");
          image.alt = "";
          return image;
        }

        if ( flavour === "video" ) {
          var video = document.createElement("video");
          video.preload = "metadata";
          video.muted = true;
          return revoking(video, "loadeddata");
        }

        var placeholder = document.createElement("span");
        placeholder.className = "compose-preview-icon";
        placeholder.textContent = flavour === "audio" ? "♫" : "📄";
        placeholder.setAttribute("aria-hidden", "true");
        return placeholder;
      }

      var flavour = flavourOf(file);

      var figure = document.createElement("figure");
      figure.className = "compose-preview compose-preview-" + flavour;

      var name = document.createElement("span");
      name.className = "compose-preview-name";
      name.textContent = file.name;

      var alt = document.createElement("input");
      alt.type = "text";
      alt.name = "media_descriptions";
      alt.className = "compose-alt";
      alt.placeholder = flavour === "image" ? "Describe this image" : "Describe this attachment";
      alt.setAttribute("aria-label", "Describe " + file.name);

      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "compose-preview-remove";
      remove.title = "Remove";
      remove.setAttribute("aria-label", "Remove " + file.name);
      remove.textContent = "×";
      remove.addEventListener("click", function () { drop(file); });

      figure.append(thumbnail(file, flavour));
      if ( flavour !== "image" ) { figure.append(name); }
      figure.append(alt, remove);
      return figure;
    }

    held.previews.replaceChildren();
    Array.prototype.forEach.call(held.files.files, function (file) {
      held.previews.append(preview(file));
    });
    held.previews.hidden = held.files.files.length === 0;
  }

  document.addEventListener("DOMContentLoaded", function () {
    function bind(form) {
      var held = parts(form);

      form.querySelector(".compose-attach").addEventListener("click", function () { held.files.click(); });
      held.files.addEventListener("change", function () { render(form); });
      held.warn.addEventListener("click", function () {
        held.warning.hidden = !held.warning.hidden;
        held.warn.setAttribute("aria-pressed", String(!held.warning.hidden));
        if ( !held.warning.hidden ) { held.warning.focus(); }
      });
      form.addEventListener("compose:reset", function () {
        held.warning.hidden = true;
        held.warn.setAttribute("aria-pressed", "false");
        render(form);
      });
    }

    function nameLanguages() {
      var options = document.querySelectorAll("#compose-languages option");
      if ( !window.Intl || !Intl.DisplayNames || !options.length ) { return; }

      var names = new Intl.DisplayNames([navigator.language || "en"], {type: "language", fallback: "none"});
      options.forEach(function (option) {
        try {
          option.label = names.of(option.value) || option.label;
        } catch (notATag) {
          option.dataset.unnamed = "malformed";
        }
      });
    }

    document.querySelectorAll("[data-editor]").forEach(bind);
    nameLanguages();
  });
})();

