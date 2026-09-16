# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import inspect
from functools import wraps
from fastapi import Request, Response


def _page(request: Request, key: str, value, dropped: str) -> str:
    return str(request.url.remove_query_params(dropped).include_query_params(**{key: value}))


def _links(request: Request, newest, oldest) -> str:
    return ", ".join([f'<{_page(request, "max_id", oldest, "since_id")}>; rel="next"',
                      f'<{_page(request, "since_id", newest, "max_id")}>; rel="prev"'])


def _asking_for_request_and_response(signature: inspect.Signature) -> inspect.Signature:
    return signature.replace(parameters=[*signature.parameters.values(),
                                         inspect.Parameter("request",
                                                           inspect.Parameter.KEYWORD_ONLY,
                                                           annotation=Request),
                                         inspect.Parameter("response",
                                                           inspect.Parameter.KEYWORD_ONLY,
                                                           annotation=Response)])


def paginated(convert=lambda rows: rows, cursor=lambda row: row.id):
    def wrapping(endpoint):
        @wraps(endpoint)
        async def paginating(*args, request: Request, response: Response, **kwargs):
            rows = await endpoint(*args, **kwargs)
            if rows:
                response.headers["Link"] = _links(request, cursor(rows[0]), cursor(rows[-1]))
            return convert(rows)

        paginating.__signature__ = _asking_for_request_and_response(inspect.signature(endpoint))
        return paginating

    return wrapping

