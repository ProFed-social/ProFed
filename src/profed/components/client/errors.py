# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import Request
from fastapi.responses import HTMLResponse

from .templating import environment


class ClientError(Exception):
    def __init__(self, status_code: int, title: str, message: str, retry: str | None = None):
        super().__init__(title)
        self.status_code = status_code
        self.title = title
        self.message = message
        self.retry = retry


async def page(request: Request, error: ClientError) -> HTMLResponse:
    template = environment().get_template("error.html")

    return HTMLResponse(template.render(title=error.title, message=error.message, retry=error.retry),
                        status_code=error.status_code)


def mount(app) -> None:
    app.add_exception_handler(ClientError, page)

