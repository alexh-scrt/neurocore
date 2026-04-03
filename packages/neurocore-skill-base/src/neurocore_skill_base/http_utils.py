"""Shared HTTP utilities for NeuroCore research skills."""
from __future__ import annotations


class RateLimitError(Exception):
    """Raised when an API returns HTTP 429. Will trigger skill retry."""

    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"Rate limited (HTTP {status_code}) at {url}")
        self.status_code = status_code
        self.url = url


class ServiceUnavailableError(Exception):
    """Raised when an API returns HTTP 503. Will trigger skill retry."""

    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"Service unavailable (HTTP {status_code}) at {url}")
        self.status_code = status_code
        self.url = url


def check_response(response: "httpx.Response") -> None:  # noqa: F821
    """Raise retryable exception for 429/503, non-retryable for other errors."""
    if response.status_code == 429:
        raise RateLimitError(response.status_code, str(response.url))
    if response.status_code == 503:
        raise ServiceUnavailableError(response.status_code, str(response.url))
    response.raise_for_status()
