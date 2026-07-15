# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from jinja2 import Environment

from profed.components.client import templating


def _write(directory, name, content):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(content, encoding="utf-8")


def test_theme_overrides_standard(tmp_path):
    standard = tmp_path / "standard"
    theme = tmp_path / "theme"
    _write(standard, "a.html", "standard-a")
    _write(theme, "a.html", "theme-a")

    env = Environment(loader=templating.build_loader(standard, theme))
    assert env.get_template("a.html").render() == "theme-a"


def test_standard_fills_gaps(tmp_path):
    standard = tmp_path / "standard"
    theme = tmp_path / "theme"
    _write(standard, "b.html", "standard-b")
    _write(theme, "a.html", "theme-a")

    env = Environment(loader=templating.build_loader(standard, theme))
    assert env.get_template("b.html").render() == "standard-b"


def test_without_theme_only_standard(tmp_path):
    standard = tmp_path / "standard"
    _write(standard, "a.html", "standard-a")

    env = Environment(loader=templating.build_loader(standard, None))
    assert env.get_template("a.html").render() == "standard-a"


def test_environment_is_cached_and_resettable(monkeypatch):
    monkeypatch.setattr(templating, "config", lambda: {})
    templating._reset_environment()

    first = templating.environment()
    assert templating.environment() is first

    templating._reset_environment()
    assert templating.environment() is not first
    templating._reset_environment()


def test_build_environment_provides_the_sanitize_filter(tmp_path):
    standard = tmp_path / "standard"
    _write(standard, "a.html", "{{ content | sanitize | safe }}")

    env = templating.build_environment(standard, None)

    assert env.get_template("a.html").render(content="<p>hi</p><script>evil()</script>") == "<p>hi</p>"


def test_build_environment_escapes_html_by_default(tmp_path):
    standard = tmp_path / "standard"
    _write(standard, "a.html", "{{ content }}")

    env = templating.build_environment(standard, None)

    assert env.get_template("a.html").render(content="<b>x</b>") == "&lt;b&gt;x&lt;/b&gt;"


def test_build_environment_prefers_the_theme(tmp_path):
    standard, theme = tmp_path / "standard", tmp_path / "theme"
    _write(standard, "a.html", "standard-a")
    _write(theme, "a.html", "theme-a")

    env = templating.build_environment(standard, theme)

    assert env.get_template("a.html").render() == "theme-a"


