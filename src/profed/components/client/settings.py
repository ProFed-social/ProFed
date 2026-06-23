# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from profed.components.client.auth import requires_login

from .api_client import api_client
from .templating import environment


logger = logging.getLogger(__name__)
router = APIRouter()

VISIBILITIES = ("public", "unlisted", "private", "direct")


def _values_from_preferences(preferences):
    return {"visibility": preferences["posting:default:visibility"],
            "sensitive": preferences["posting:default:sensitive"],
            "language": preferences["posting:default:language"]}


def _values_from_source(source):
    return {"visibility": source["privacy"],
            "sensitive": source["sensitive"],
            "language": source["language"]}


def _submitted(form):
    return {"visibility": form.get("visibility"),
            "sensitive": form.get("sensitive") is not None,
            "language": form.get("language", "")}


def _credentials_payload(values):
    return {"source[privacy]": values["visibility"],
            "source[sensitive]": "true" if values["sensitive"] else "false",
            "source[language]": values["language"]}


async def _languages():
    response = await api_client().get("/api/v2/instance")
    return response.json().get("languages", []) if response.status_code == 200 else []


def _render(name, values, languages, saved=False, error=None, current_username=None):
    return environment().get_template(name).render(values=values,
                                                   visibilities=VISIBILITIES,
                                                   languages=languages,
                                                   saved=saved,
                                                   error=error,
                                                   current_username=current_username)


@router.get("/settings")
@requires_login
async def settings(request: Request, session):
    preferences = await api_client().get("/api/v1/preferences", token=session["token"])
    preferences.raise_for_status()
    return HTMLResponse(_render("settings.html",
                                _values_from_preferences(preferences.json()),
                                await _languages(),
                                current_username=session.get("username")))


@router.post("/settings")
@requires_login
async def update_settings(request: Request, session):
    submitted = _submitted(await request.form())
    response = await api_client().patch("/api/v1/accounts/update_credentials",
                                        token=session["token"],
                                        data=_credentials_payload(submitted))

    languages = await _languages()
    if response.status_code == 200:
        return HTMLResponse(_render("settings_form.html",
                                    _values_from_source(response.json()["source"]),
                                    languages,
                                    saved=True))

    return HTMLResponse(_render("settings_form.html",
                                submitted,
                                languages,
                                error="Could not save settings."),
                        status_code=response.status_code)

