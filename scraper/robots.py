"""robots.txt compliance checks before scraping a URL."""

from __future__ import annotations

import urllib.robotparser
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

from .http_client import HttpClient
from .logger import get_logger

log = get_logger(__name__)


class RobotsChecker:
    """Caches robots.txt parsers per domain and checks URL allow-lists."""

    def __init__(self, http_client: Optional[HttpClient] = None) -> None:
        self.http_client = http_client or HttpClient(min_delay=0.5, timeout=10.0)
        self._parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.user_agent = "*"

    def _parser_for(self, url: str) -> Optional[urllib.robotparser.RobotFileParser]:
        domain = urlparse(url).netloc
        if domain in self._parsers:
            return self._parsers[domain]

        robots_url = urljoin(url, "/robots.txt")
        parser = urllib.robotparser.RobotFileParser()
        try:
            html = self.http_client.get_html(robots_url)
            if html:
                parser.parse(html.splitlines())
            else:
                # No robots.txt => treat everything as allowed.
                parser.parse([])
        except Exception as exc:  # noqa: BLE001 - be permissive on robots failure
            log.warning("Could not load robots.txt for %s: %s", domain, exc)
            parser.parse([])

        self._parsers[domain] = parser
        return parser

    def can_fetch(self, url: str) -> bool:
        """Return True if ``url`` may be fetched per robots.txt."""
        parser = self._parser_for(url)
        if parser is None:
            return True
        allowed = parser.can_fetch(self.user_agent, url)
        if not allowed:
            log.info("robots.txt disallows: %s", url)
        return allowed
