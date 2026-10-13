// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
    document.addEventListener("DOMContentLoaded", function () {
        function bind(form) {
            var held = {files: form.querySelector(".compose-files"),
                        previews: form.querySelector(".compose-previews"),
                        warning: form.querySelector(".compose-warning"),
                        warn: form.querySelector(".compose-warn"),
                        error: form.querySelector(".compose-error")};
            var chosen = new DataTransfer();

            function render() {
                function preview(file) {
                    function flavourOf(file) {
                        var type = file.type || "";
                        return type.indexOf("image/") === 0 ? "image" :
                               type.indexOf("video/") === 0 ? "video" :
                               type.indexOf("audio/") === 0 ? "audio" :
                               "file";
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

                    function drop(dropped) {
                        var kept = new DataTransfer();
                        Array.prototype.forEach.call(chosen.files, function (file) {
                            if ( file !== dropped ) { kept.items.add(file); }
                        });

                        chosen = kept;
                        render();
                    }

                    var flavour = flavourOf(file);

                    var figure = document.createElement("figure");
                    figure.className = "compose-preview compose-preview-" + flavour;
                    figure.file = file;

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

                function shown(file) {
                    return Array.prototype.find.call(held.previews.children, function (figure) {
                        return figure.file === file;
                    });
                }

                var figures = Array.prototype.map.call(chosen.files, function (file) {
                    return shown(file) || preview(file);
                });

                held.files.files = chosen.files;
                held.previews.replaceChildren.apply(held.previews, figures);
                held.previews.hidden = figures.length === 0;
            }

            function take(picked) {
                function known(candidate) {
                    return Array.prototype.some.call(chosen.files, function (file) {
                        return file.name === candidate.name &&
                               file.size === candidate.size &&
                               file.lastModified === candidate.lastModified;
                    });
                }

                Array.prototype.forEach.call(picked, function (file) {
                    if ( !known(file) ) { chosen.items.add(file); }
                });

                render();
            }

            function forget() {
                chosen = new DataTransfer();
                render();
            }

            function complain(text) {
                held.error.textContent = text;
                held.error.hidden = !text;
            }

            form.querySelector(".compose-attach").addEventListener("click", function () { held.files.click(); });
            held.files.addEventListener("change", function () { take(held.files.files); });
            held.warn.addEventListener("click", function () {
                held.warning.hidden = !held.warning.hidden;
                held.warn.setAttribute("aria-pressed", String(!held.warning.hidden));
                if ( !held.warning.hidden ) { held.warning.focus(); }
            });
            form.addEventListener("htmx:beforeRequest", function () { complain(""); });
            form.addEventListener("htmx:responseError", function (event) {
                function stated() {
                    try {
                        return JSON.parse(event.detail.xhr.responseText).detail;
                    } catch (notJson) {
                        return "";
                    }
                }
                complain(stated() || "Sending failed. Please try again.");
            });
            form.addEventListener("compose:reset", function () {
                held.warning.hidden = true;
                held.warn.setAttribute("aria-pressed", "false");
                complain("");
                forget();
            });
        }

        function nameLanguages() {
            function naming() {
                try {
                    return new Intl.DisplayNames([navigator.language || "en"],
                                                 {type: "language", fallback: "none"});
                } catch (notALocale) {
                    return new Intl.DisplayNames(["en"], {type: "language", fallback: "none"});
                }
            }

            var options = document.querySelectorAll("#compose-languages option");
            if ( !window.Intl || !Intl.DisplayNames || !options.length ) { return; }

            var names = naming();
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

