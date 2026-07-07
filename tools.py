"""
VyaparSathi Tools
==============
Provides the agent with capabilities:
  1. Web Search   â€“ via DuckDuckGo (free, no API key required)
  2. Page Scrape  â€“ via httpx + BeautifulSoup (extracts clean text)

Features:
  â€¢ Thread-safe async wrappers
  â€¢ Graceful fallback on search failure (returns empty, doesn't crash)
  â€¢ Content capping to stay within LLM context budgets
"""

import asyncio
from typing import List, Dict

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS


# â”€â”€ Web Search Tool â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def search_web(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo and return structured results.

    Each result contains:
      - title   : page title
      - url     : page URL
      - snippet : text snippet from the search result

    Includes fallback: if DuckDuckGo fails, returns an empty list
    so the agent can continue with whatever data it has.
    """
    def _search() -> list:
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception:
            return []

    loop = asyncio.get_event_loop()
    raw_results = await loop.run_in_executor(None, _search)

    return [
        {
            "title":   r.get("title", ""),
            "url":     r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in raw_results
    ]


# â”€â”€ Page Scraper Tool â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def scrape_page(url: str, timeout: float = 10.0) -> str:
    """
    Fetch a web page and extract its main text content.

    Strips scripts, styles, navbars, and footers so the agent
    receives only useful prose.  Content is capped at 3 000 chars
    to stay within LLM context budgets.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
        ) as client:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove non-content elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            return text[:3000]

    except Exception as exc:
        return f"[Scrape Error] {url}: {exc}"

