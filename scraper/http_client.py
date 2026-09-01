"""HTTP client with retries, user-agent rotation and polite rate limiting."""

from __future__ import annotations

import random
import threading
import time
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logger import get_logger

log = get_logger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


class RateLimiter:
    """Ensures a minimum delay between requests to the same domain."""

    def __init__(self, min_delay: float = 1.0) -> None:
        self.min_delay = min_delay
        self._last_request: Dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, url: str) -> None:
        domain = urlparse(url).netloc
        with self._lock:
            now = time.monotonic()
            last = self._last_request.get(domain, 0.0)
            wait_for = self.min_delay - (now - last)
            if wait_for > 0:
                log.debug("Rate limiting %.2fs for %s", wait_for, domain)
                time.sleep(wait_for)
            self._last_request[domain] = time.monotonic()


class HttpClient:
    """A requests.Session wrapper adding retries, UA rotation and rate limits."""

    def __init__(
        self,
        timeout: float = 15.0,
        min_delay: float = 1.0,
        retries: int = 3,
        backoff_factor: float = 1.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.timeout = timeout
        self.min_delay = min_delay
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.base_headers = headers or {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.session = requests.Session()
        self._configure_retries()
        self.rate_limiter = RateLimiter(min_delay)

    def _configure_retries(self) -> None:
        retry = Retry(
            total=self.retries,
            read=self.retries,
            connect=self.retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _headers(self) -> Dict[str, str]:
        headers = dict(self.base_headers)
        headers["User-Agent"] = random.choice(USER_AGENTS)
        return headers

    def get(self, url: str, **kwargs) -> requests.Response:
        """Perform a GET request with rate limiting and UA rotation."""
        self.rate_limiter.wait(url)
        log.info("GET %s", url)
        timeout = kwargs.pop("timeout", self.timeout)
        response = self.session.get(url, headers=self._headers(), timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    def get_html(self, url: str, **kwargs) -> str:
        """Return the HTML text of a GET response."""
        try:
            response = self.get(url, **kwargs)
            if response.encoding is None or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding
            return response.text
        except requests.RequestException as exc:
            log.warning("Request failed for %s: %s", url, exc)
            return ""
