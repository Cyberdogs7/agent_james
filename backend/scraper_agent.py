import asyncio
import httpx
from bs4 import BeautifulSoup
import json
import urllib.parse
import logging

# Configure logging
logger = logging.getLogger(__name__)

class ScraperAgent:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def _fetch(self, url: str) -> str:
        """Helper to fetch a URL with error handling."""
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=self.headers) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
                return ""

    async def search_google(self, query: str, num_results: int = 3) -> list[str]:
        """
        Performs a search (currently using DuckDuckGo HTML as a proxy for 'Google search'
        to avoid API keys/captchas) and returns a list of result URLs.
        """
        # Using DuckDuckGo HTML interface which is easier to scrape than Google
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        html = await self._fetch(search_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        urls = []

        # DuckDuckGo HTML results are typically in 'a.result__a'
        for link in soup.select('a.result__a'):
            url = link.get('href')
            if url:
                urls.append(url)
                if len(urls) >= num_results:
                    break

        return urls

    async def extract_structured_data(self, url: str) -> dict:
        """
        Visits a URL and extracts structured data (JSON-LD, OpenGraph, Meta).
        """
        html = await self._fetch(url)
        if not html:
            return {"url": url, "error": "Failed to fetch content"}

        soup = BeautifulSoup(html, 'html.parser')
        data = {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "description": "",
            "json_ld": [],
            "open_graph": {},
            "meta_tags": {}
        }

        # 1. Extract Meta Description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            data["description"] = desc_tag.get("content", "")

        # 2. Extract JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                if script.string:
                    json_content = json.loads(script.string)
                    data["json_ld"].append(json_content)
            except json.JSONDecodeError:
                continue

        # 3. Extract Open Graph
        for meta in soup.find_all("meta", property=lambda x: x and x.startswith("og:")):
            prop = meta.get("property")
            content = meta.get("content")
            if prop and content:
                data["open_graph"][prop] = content

        # 4. Extract other useful Meta tags (e.g., twitter cards, keywords)
        for meta in soup.find_all("meta"):
            name = meta.get("name")
            content = meta.get("content")
            if name and content and name not in ["description", "viewport"]:
                data["meta_tags"][name] = content

        return data

    async def search_and_scrape(self, query: str) -> list[dict]:
        """
        Orchestrates the search and scrape process:
        1. Search for the query.
        2. Scrape the top results concurrently.
        3. Return a list of structured data objects.
        """
        # 1. Get URLs
        urls = await self.search_google(query)
        if not urls:
            return []

        # 2. Scrape concurrently
        tasks = [self.extract_structured_data(url) for url in urls]
        results = await asyncio.gather(*tasks)

        return results
