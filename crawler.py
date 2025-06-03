import requests
import json
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentCrawler:
    def __init__(self, serper_api_key: str):
        """
        Initialize the Content Crawler with Serper API key
        
        Args:
            serper_api_key (str): Your Serper API key
        """
        self.serper_api_key = serper_api_key
        self.serper_base_url = "https://google.serper.dev/search"
        self.headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_related_topics(self, query: str, num_results: int = 10, 
                            country: str = 'us', language: str = 'en') -> Dict:
        """
        Search for content using Serper API
        
        Args:
            query (str): Search query
            num_results (int): Number of results to return
            country (str): Country code for search localization
            language (str): Language code for search
            
        Returns:
            Dict: Search results from Serper API
        """
        payload = {
            'q': query,
            'num': num_results,
            'gl': country,
            'hl': language
        }
        
        try:
            response = requests.post(
                self.serper_base_url,
                headers=self.headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching with Serper API: {e}")
            return {}
    
    def extract_internal_links(self, soup: BeautifulSoup, base_url: str, max_links: int = 10) -> List[str]:
        """
        Extract internal links from a webpage
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            base_url (str): Base URL for resolving relative links
            max_links (int): Maximum number of internal links to extract
            
        Returns:
            List[str]: List of internal links
        """
        base_domain = urlparse(base_url).netloc
        internal_links = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            
            if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
            
            full_url = urljoin(base_url, href)
            parsed_url = urlparse(full_url)
            
            if parsed_url.netloc == base_domain:
                clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                if clean_url != base_url and clean_url not in internal_links:
                    internal_links.add(clean_url)
                    
                    if len(internal_links) >= max_links:
                        break
        
        return list(internal_links)
    
    def extract_content_from_url(self, url: str, timeout: int = 10) -> Dict[str, str]:
        """
        Extract content from a given URL and optionally its internal links
        
        Args:
            url (str): URL to extract content from
            timeout (int): Request timeout in seconds
            crawl_internal (bool): Whether to crawl internal links
            max_internal_links (int): Maximum number of internal links to crawl
            
        Returns:
            Dict: Extracted content with title, text, metadata, and internal links content
        """
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title found"

            content_selectors = [
                'article', 'main', '[role="main"]', 
                '.content', '.post-content', '.entry-content',
                '.article-content', '.post-body'
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content_text = content_element.get_text(separator=' ', strip=True)
                    break
            
            if not content_text:
                body = soup.find('body')
                if body:
                    content_text = body.get_text(separator=' ', strip=True)
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            

            content_text = ' '.join(content_text.split())
            try:
                content_text = content_text.encode('utf-8', errors='ignore').decode('utf-8')
            except Exception as e:
                logger.warning(f"Encoding issue with content at {url}: {e}")
                content_text = content_text.encode('utf-8', errors='replace').decode('utf-8')

            
            # Base result
            result = {
                'title': title_text,
                'content': content_text[:5000],  # Limit content length
                'description': description,
                'url': url,
                'word_count': len(content_text.split()),
                'status': 'success',
                'internal_links': []
            }
            
            internal_links = self.extract_internal_links(soup, url)
            
            result['internal_links'] = internal_links
            result['internal_links_count'] = len(internal_links)
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return {
                'title': '',
                'content': '',
                'description': '',
                'url': url,
                'word_count': 0,
                'status': f'error: {str(e)}',
                'internal_links': []
            }
        except Exception as e:
            logger.error(f"Error parsing content from {url}: {e}")
            return {
                'title': '',
                'content': '',
                'description': '',
                'url': url,
                'word_count': 0,
                'status': f'parsing error: {str(e)}',
                'internal_links': []
            }
    
    def crawl_related_content(self, query: str, max_results: int = 5, 
                            delay: float = 1.0) -> List[Dict]:
        """
        Main method to crawl content for related topics
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of URLs to crawl
            delay (float): Delay between requests in seconds
            crawl_internal_links (bool): Whether to crawl internal links from each site
            max_internal_per_site (int): Maximum internal links to crawl per site
            
        Returns:
            List[Dict]: List of crawled content with metadata
        """
        logger.info(f"Starting content crawl for query: '{query}'")
        search_results = self.search_related_topics(query, max_results)
        
        if not search_results or 'organic' not in search_results:
            logger.error("No search results found")
            return []
        
        crawled_content = []
        urls_to_crawl = []
        
        for result in search_results['organic'][:max_results]:
            urls_to_crawl.append({
                'url': result.get('link', ''),
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'position': result.get('position', 0)
            })
        
        for i, url_info in enumerate(urls_to_crawl):
            logger.info(f"Crawling {i+1}/{len(urls_to_crawl)}: {url_info['url']}")
            
            content = self.extract_content_from_url(
                url_info['url'], 

            )
            
            combined_content = {
                **content,
                'search_title': url_info['title'],
                'search_snippet': url_info['snippet'],
                'search_position': url_info['position'],
                'crawled_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            crawled_content.append(combined_content)
            
            if i < len(urls_to_crawl) - 1:
                time.sleep(delay)
        
        logger.info(f"Crawling completed. {len(crawled_content)} pages processed.")
        return crawled_content
    # def save_results(self, results: List[Dict], filename: str = None):
    #     """
    #     Save crawled results to JSON file
        
    #     Args:
    #         results (List[Dict]): Crawled content results
    #         filename (str): Output filename (optional)
    #     """
    #     if not filename:
    #         timestamp = time.strftime('%Y%m%d_%H%M%S')
    #         filename = f'crawled_content_{timestamp}.json'
        
    #     try:
    #         with open(filename, 'w', encoding='utf-8') as f:
    #             json.dump(results, f, indent=2, ensure_ascii=False)
    #         logger.info(f"Results saved to {filename}")
    #     except Exception as e:
    #         logger.error(f"Error saving results: {e}")

# def main():
#     """
#     Example usage of the ContentCrawler
#     """
#     # Initialize crawler with your Serper API key
#     API_KEY = "5538f5b0ddbf20f1f349364f0895f17a19581c64"  # Replace with your actual API key
#     crawler = ContentCrawler(API_KEY)
    
#     # Example queries
#     queries = [
#         "artificial intelligence trends 2024"
#         # "sustainable energy solutions",
#         # "remote work productivity tips"
#     ]
    
#     for query in queries:
#         print(f"\n{'='*50}")
#         print(f"Crawling content for: {query}")
#         print(f"{'='*50}")
        
#         # Crawl content
#         results = crawler.crawl_related_content(query, max_results=3, delay=1.0)
        
#         # Generate summary
#         summary = crawler.generate_summary_report(results)
        
#         print(f"\nSummary Report:")
#         print(f"- Total URLs processed: {summary.get('total_urls', 0)}")
#         print(f"- Successful crawls: {summary.get('successful_crawls', 0)}")
#         print(f"- Success rate: {summary.get('success_rate', 0)}%")
#         print(f"- Total words extracted: {summary.get('total_words_extracted', 0)}")
        
#         print(f"\nSources:")
#         for i, source in enumerate(summary.get('sources', []), 1):
#             print(f"{i}. {source}")
        
#         # Save results
#         timestamp = time.strftime('%Y%m%d_%H%M%S')
#         filename = f"crawl_{query.replace(' ', '_')}_{timestamp}.json"
#         crawler.save_results(results, filename)
        
#         print(f"\nDetailed results saved to: {filename}")


# if __name__ == "__main__":
#     main()