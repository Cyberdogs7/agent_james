import asyncio
import httpx
from bs4 import BeautifulSoup
import json
import logging
from typing import List, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)


class ScraperAgent:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self._browser_agent = None

    def set_browser_agent(self, browser_agent):
        """Set a browser agent for fallback search."""
        self._browser_agent = browser_agent

    async def _fetch(self, url: str, params: dict = None) -> str:
        """Helper to fetch a URL with error handling."""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=self.headers) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
                return ""

    async def search_duckduckgo(self, query: str, num_results: int = 5) -> List[str]:
        """Search using DuckDuckGo HTML interface."""
        search_url = "https://html.duckduckgo.com/html/"
        html = await self._fetch(search_url, params={"q": query})
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        urls = []
        for link in soup.select('a.result__a'):
            url = link.get('href')
            if url and url.startswith('http'):
                urls.append(url)
                if len(urls) >= num_results:
                    break
        return urls

    async def search_startpage(self, query: str, num_results: int = 5) -> List[str]:
        """Search using Startpage (privacy-focused Google proxy)."""
        search_url = "https://www.startpage.com/sp/search"
        html = await self._fetch(search_url, params={"query": query, "cat": "web"})
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        urls = []
        for result in soup.select('a.result-link'):
            url = result.get('href')
            if url and url.startswith('http'):
                urls.append(url)
                if len(urls) >= num_results:
                    break
        return urls

    async def search_browser(self, query: str, num_results: int = 5) -> List[str]:
        """Fallback: Use browser agent for search when HTTP scraping fails."""
        if not self._browser_agent:
            return []

        try:
            await self._browser_agent._ensure_browser()
            page = self._browser_agent.page
            if not page:
                return []

            # Navigate to Google and search
            await page.goto(f"https://www.google.com/search?q={query}", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Extract search result URLs
            urls = await page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href]');
                    for (const link of links) {
                        const href = link.href;
                        if (href && href.startsWith('http') && 
                            !href.includes('google.com') && 
                            !href.includes('youtube.com/results')) {
                            results.push(href);
                            if (results.length >= 10) break;
                        }
                    }
                    return results;
                }
            """)
            return urls[:num_results] if urls else []
        except Exception as e:
            logger.error(f"Browser search failed: {e}")
            return []

    async def search_google(self, query: str, num_results: int = 5) -> List[str]:
        """
        Performs a search using multiple providers with fallback.
        Returns a list of result URLs.
        """
        # Try DuckDuckGo first
        urls = await self.search_duckduckgo(query, num_results)
        if urls:
            return urls

        # Fallback to Startpage
        urls = await self.search_startpage(query, num_results)
        if urls:
            return urls

        # Final fallback: browser-based search
        urls = await self.search_browser(query, num_results)
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
            "title": soup.title.string.strip() if soup.title and soup.title.string else "",
            "description": "",
            "content": "",
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

        # 4. Extract other useful Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name")
            content = meta.get("content")
            if name and content and name not in ["description", "viewport"]:
                data["meta_tags"][name] = content

        # 5. Extract main content text (first 2000 chars)
        try:
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Get text content
            text = soup.get_text(separator=' ', strip=True)
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            data["content"] = text[:2000]
        except Exception:
            data["content"] = ""

        return data

    async def search_and_scrape(self, query: str) -> List[dict]:
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

        # 2. Scrape concurrently (limit to top 5)
        tasks = [self.extract_structured_data(url) for url in urls[:5]]
        results = await asyncio.gather(*tasks)

        # Filter out failed results
        return [r for r in results if r and not r.get("error")]

    async def deep_scrape(self, query: str, max_results: int = 10) -> List[dict]:
        """
        Enhanced scrape that uses browser for JavaScript-heavy sites.
        """
        urls = await self.search_google(query, max_results)
        if not urls:
            return []

        results = []
        for url in urls[:max_results]:
            try:
                data = await self.extract_structured_data(url)
                if data and not data.get("error"):
                    results.append(data)
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                continue

        return results