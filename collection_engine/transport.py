"""Sequential HTTP with bounded retries; no 401/403/redirect retries."""
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from .contracts import CollectionError


class HttpTransport:
    def __init__(self, interval=3.1, max_attempts=3, max_wait=30, session=None,
                 sleep=time.sleep, clock=time.monotonic, jitter=random.random):
        self.interval, self.max_attempts, self.max_wait = interval, max_attempts, max_wait
        self.session = session or requests.Session()
        self.sleep, self.clock, self.jitter = sleep, clock, jitter
        self.last_start = None
        self.request_count = 0

    @staticmethod
    def retry_seconds(value):
        if not value:
            return None
        try:
            return max(0, float(value))
        except ValueError:
            try:
                return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                return None

    def get_json(self, url, **kwargs):
        if not url.startswith("https://"):
            raise CollectionError("insecure_transport")
        for attempt in range(self.max_attempts):
            if self.last_start is not None:
                self.sleep(max(0, self.interval - (self.clock() - self.last_start)))
            self.last_start = self.clock()
            self.request_count += 1
            try:
                response = self.session.get(url, timeout=20, allow_redirects=False, **kwargs)
            except requests.RequestException:
                if attempt + 1 == self.max_attempts:
                    raise CollectionError("access_error") from None
                self.sleep(min(self.max_wait, 2 ** attempt + self.jitter()))
                continue
            status = response.status_code
            if status == 200:
                try:
                    body = response.json()
                except ValueError:
                    raise CollectionError("parsing_error", status) from None
                if not isinstance(body, dict):
                    raise CollectionError("parsing_error", status)
                return body
            if status in (429, 500, 502, 503, 504):
                wait = self.retry_seconds(response.headers.get("Retry-After"))
                wait = max(wait or 0, 2 ** attempt + self.jitter())
                if attempt + 1 == self.max_attempts or wait > self.max_wait:
                    raise CollectionError("rate_limit" if status == 429 else "access_error", status, wait)
                self.sleep(wait)
                continue
            category = {401: "authentication_failed", 403: "permission_denied"}.get(status, "access_error")
            raise CollectionError(category, status)
        raise CollectionError("access_error")
