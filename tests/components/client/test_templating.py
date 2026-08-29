# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone

import pytest
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


NOW = datetime(2026, 8, 24, 20, 17, tzinfo=timezone.utc)


def _ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat()


@pytest.mark.parametrize("minutes, expected", [(0, "just now"),
                                               (1, "a minute ago"),
                                               (5, "5 minutes ago"),
                                               (60, "an hour ago"),
                                               (300, "5 hours ago"),
                                               (1440, "a day ago"),
                                               (2880, "2 days ago"),
                                               (10080, "a week ago"),
                                               (43200, "a month ago"),
                                               (100000, "2 months ago"),
                                               (525600, "a year ago"),
                                               (1100000, "2 years ago")])
def test_relative_time_renders_a_colloquial_distance(minutes, expected):
    assert templating.relative_time(_ago(minutes), NOW) == expected


def test_relative_time_measures_against_now_by_default():
    assert templating.relative_time(datetime.now(timezone.utc).isoformat()) == "just now"


def test_relative_time_assumes_utc_for_a_naive_timestamp():
    assert templating.relative_time("2026-08-24T20:12:00", NOW) == "5 minutes ago"


def test_relative_time_survives_an_unparsable_timestamp():
    assert templating.relative_time("kein datum") == ""


def test_local_minutes_drops_seconds_and_the_timezone():
    assert templating.local_minutes("2026-08-24T20:17:43+00:00") == "2026-08-24 20:17"


def test_local_minutes_accepts_a_trailing_z():
    assert templating.local_minutes("2026-08-24T20:17:43Z") == "2026-08-24 20:17"


def test_local_minutes_survives_an_unparsable_timestamp():
    assert templating.local_minutes(None) == ""


def test_build_environment_registers_the_time_filters(tmp_path):
    standard = tmp_path / "standard"
    _write(standard, "a.html", "{{ t | relative_time }}|{{ t | local_minutes }}")

    env = templating.build_environment(standard, None)

    assert env.get_template("a.html").render(t="2026-08-24T20:17:43Z").endswith("|2026-08-24 20:17")


def test_a_https_url_becomes_a_rel_me_link():
    assert templating.link_field("https://a.test/x") == '<a rel="me" href="https://a.test/x">https://a.test/x</a>'


def test_a_http_url_becomes_a_rel_me_link():
    assert templating.link_field("http://a.test/x") == '<a rel="me" href="http://a.test/x">http://a.test/x</a>'


def test_plain_text_stays_plain():
    assert templating.link_field("Hamburg") == "Hamburg"


def test_markup_in_a_url_is_escaped():
    linked = templating.link_field('https://a.test/"><script>x</script>')
    assert "<script>" not in linked


def test_markup_in_plain_text_is_sanitised():
    assert "<script>" not in templating.link_field("<script>alert(1)</script>")

