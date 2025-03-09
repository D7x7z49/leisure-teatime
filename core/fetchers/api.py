# core/fetchers/api.py
from dataclasses import is_dataclass, asdict, dataclass
from typing import Any
from playwright.async_api import Page, APIRequestContext, APIResponse

async def fetch(page: Page, url: str, method: str, data: Any = None) -> APIResponse:
    request: APIRequestContext = page.request
    request_data = None
    params = None
    if data is not None:
        if not is_dataclass(data):
            raise ValueError("The 'data' parameter must be a dataclass instance.")
        request_data = asdict(data)
        if method.upper() == "GET":
            params = request_data
            request_data = None

    method = method.upper()
    if method == "GET":
        response = await request.get(url, params=params)
    elif method == "POST":
        response = await request.post(url, data=request_data)
    else:
        raise ValueError(f"Unsupported method: {method}")

    return response


from playwright.sync_api import Page, APIRequestContext, APIResponse

def get(page: Page, url: str, method: str, data: Any = None) -> APIResponse:
    request: APIRequestContext = page.request
    request_data = None
    params = None
    if data is not None:
        if not is_dataclass(data):
            raise ValueError("The 'data' parameter must be a dataclass instance.")
        request_data = asdict(data)
        if method.upper() == "GET":
            params = request_data
            request_data = None

    method = method.upper()
    if method == "GET":
        response = request.get(url, params=params)
    elif method == "POST":
        response = request.post(url, data=request_data)
    else:
        raise ValueError(f"Unsupported method: {method}")

    return response


