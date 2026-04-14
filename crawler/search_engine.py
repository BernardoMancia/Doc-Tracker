import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ddgs import DDGS

from config.settings import settings
from crawler.url_filter import URLFilter

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredURL:
    url: str
    title: str
    snippet: str
    source_dork: str
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SearchEngine:

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    ]

    def __init__(self, url_filter: URLFilter | None = None):
        self.url_filter = url_filter or URLFilter()
        self._seen_urls: set[str] = set()

    async def _search_single_dork(self, dork: str) -> list[DiscoveredURL]:
        results = []
        try:
            with DDGS(proxy=settings.proxy_url or None) as ddgs:
                search_results = ddgs.text(
                    dork,
                    max_results=settings.max_results_per_dork,
                    region="br-pt",
                )
                for r in search_results:
                    url = r.get("href", "")
                    if not url or url in self._seen_urls:
                        continue
                    if not self.url_filter.is_valid(url):
                        continue
                    self._seen_urls.add(url)
                    results.append(DiscoveredURL(
                        url=url,
                        title=r.get("title", ""),
                        snippet=r.get("body", ""),
                        source_dork=dork,
                    ))
        except Exception as e:
            logger.warning("Search failed for dork [%s]: %s", dork[:80], e)
        return results

    async def search(self, dorks: list[str]) -> list[DiscoveredURL]:
        all_results: list[DiscoveredURL] = []
        for i, dork in enumerate(dorks):
            logger.info("Executing dork %d/%d: %s", i + 1, len(dorks), dork[:100])
            results = await self._search_single_dork(dork)
            all_results.extend(results)
            if results:
                logger.info("Found %d results for dork %d", len(results), i + 1)
            delay = random.uniform(settings.search_delay_min, settings.search_delay_max)
            await asyncio.sleep(delay)
        logger.info("Search complete: %d unique URLs from %d dorks", len(all_results), len(dorks))
        return all_results
