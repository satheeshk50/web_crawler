import asyncio
import os
from firecrawl import AsyncFirecrawlApp
from typing import List, Dict

class URLScraper:
    def __init__(self, api_key: str):
        self.app = AsyncFirecrawlApp(api_key=api_key)
    
    async def scrape_url(self, url: str, timeout: int = 30) -> Dict:
        """
        Scrape a single URL and return the content with timeout.
        """
        try:
            print(f"Scraping: {url}")
            # Add timeout to the scrape operation
            response = await asyncio.wait_for(
                self.app.scrape_url(
                    url=url,
                    formats=['markdown'],
                    only_main_content=True
                ),
                timeout=timeout
            )
            print(f"Successfully scraped: {url}")
            return {
                'url': url,
                'success': True,
                'content': response
            }
        except asyncio.TimeoutError:
            print(f"Timeout scraping {url}")
            return {
                'url': url,
                'success': False,
                'content': '',
                'error': f'Timeout after {timeout} seconds'
            }
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return {
                'url': url,
                'success': False,
                'content': '',
                'error': str(e)
            }
    
    async def scrape_multiple_urls(self, urls: List[str], timeout: int = 30, max_concurrent: int = 3) -> List[Dict]:
        """
        Scrape multiple URLs with concurrency limit and timeout.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_url(url, timeout)
        
        try:
            tasks = [scrape_with_semaphore(url) for url in urls]
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout * len(urls)  
            )
            return results
        except asyncio.TimeoutError:
            return [{'url': url, 'success': False, 'error': 'Overall operation timeout'} for url in urls]