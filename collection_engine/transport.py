"""Sequential HTTPS requests with bounded retries and credential-safe errors."""
import math
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from .contracts import CollectionError


def _finite_number(value, positive=False):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and (value > 0 if positive else value >= 0))


class HttpTransport:
    def __init__(self, interval=3.1, max_attempts=3, max_wait=30, session=None,
                 sleep=time.sleep, clock=time.monotonic, jitter=random.random, timeout=20):
        if not _finite_number(interval) or not _finite_number(max_wait):
            raise ValueError("HTTP interval and max_wait must be finite and nonnegative")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 10:
            raise ValueError("HTTP max_attempts must be an integer from 1 to 10")
        timeouts = timeout if isinstance(timeout, tuple) else (timeout,)
        if len(timeouts) not in (1, 2) or not all(_finite_number(value, True) for value in timeouts):
            raise ValueError("HTTP timeout must be a positive number or connect/read pair")
        self.interval, self.max_attempts, self.max_wait = interval, max_attempts, max_wait
        self.timeout = timeout
        self.session = session or requests.Session()
        self.sleep, self.clock, self.jitter = sleep, clock, jitter
        self.last_start = None
        self.request_count = 0

    @staticmethod
    def retry_seconds(value):
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            seconds = float(value)
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                seconds = (date - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                return None
        # JSON reports and time.sleep cannot safely handle NaN or infinity.
        return max(0, seconds) if math.isfinite(seconds) else None

    def get_json(self, url, **kwargs):
        return self._json_request(self.session.get, url, **kwargs)

    def get_text(self, url, **kwargs):
        return self._json_request(self.session.get, url, as_text=True, **kwargs)

    def post_json(self, url, **kwargs):
        """Use only for repeatable operations such as client-credentials OAuth."""
        return self._json_request(self.session.post, url, **kwargs)

    def _json_request(self, request, url, as_text=False, **kwargs):
        if not isinstance(url, str) or not url.startswith("https://"):
            raise CollectionError("insecure_transport")
        # Transport owns these options so callers cannot disable its bounds.
        if "timeout" in kwargs or "allow_redirects" in kwargs:
            raise ValueError("Configure timeout on HttpTransport; redirects are disabled")
        for attempt in range(self.max_attempts):
            if self.last_start is not None:
                self.sleep(max(0, self.interval - (self.clock() - self.last_start)))
            self.last_start = self.clock()
            self.request_count += 1
            try:
                response = request(url, timeout=self.timeout, allow_redirects=False, **kwargs)
            except (requests.Timeout, requests.ConnectionError) as error:
                if attempt + 1 == self.max_attempts:
                    category = "timeout" if isinstance(error, requests.Timeout) else "access_error"
                    raise CollectionError(category) from None
                self.sleep(min(self.max_wait, 2 ** attempt + self.jitter()))
                continue
            except requests.RequestException:
                raise CollectionError("access_error") from None
            try:
                status = response.status_code
                if status == 200:
                    if as_text:
                        if not isinstance(response.text, str):
                            raise CollectionError("parsing_error", status)
                        return response.text
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
                else:
                    category = {401: "authentication_failed", 403: "permission_denied"}.get(status, "access_error")
                    raise CollectionError(category, status)
            finally:
                response.close()
            self.sleep(wait)
        raise CollectionError("access_error")
