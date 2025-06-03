from mcp.server.fastmcp import FastMCP,Server
from dotenv import load_dotenv
import httpx
import json
import asyncio
from typing import List
import os
from crawler import ContentCrawler
from crawler2 import URLScraper
load_dotenv()

mcp = FastMCP("content crawler")

# crawler = ContentCrawler(os.getenv("SERPER_API_KEY"))
crawler = ContentCrawler("5538f5b0ddbf20f1f349364f0895f17a19581c64")
# crawler2 = URLScraper(os.getenv("FIRECRAWL_API_KEY"))
crawler2 = URLScraper("fc-1290f6ebe83f4641a1a04e3e03dd45fb")

@mcp.tool()  
async def get_content(topic: str) -> str:
  """
  Tool is used for explanaing a topic by searching the web and fetching content along with recent blogs with urls from the top two results.
  
  This tool performs a web search using the Serper API, retrieves the first two search results, 
  and fetches the full text content from their URLs. The aggregated content is returned for 
  further processing by the LLM, which generates an explanation or summary for the user.

  Args:
      query (str): The topic or keyword to search for online.

  Returns:
      str: Combined textual content from the top two relevant web pages.

  Raises:
      Exception: If an error occurs during the search or while fetching web pages.

  Example:
      get_content("Introduction to Machine Learning")
      # Returns the full text from the first two web pages found on the topic "Introduction to Machine Learning".
  """
  try:
    results = crawler.crawl_related_content(topic, max_results=3, delay=1.0)
    
    text = """you got the  content from the web and internal links 
    you need to decide which internal links have useful content which is helpful to explain the topic to the user
    after that you need to call the tool to get the content from the internal links by passing the list[urls] to that tool one by one
    remember , pass the required the urls only that too in the list of strings format. provide the blogs summary along with the urls to the user"""
    results.append({'prompt for using next tool': text})
    return results
  except Exception as e:
        return f"Error during execution: {str(e)}"

@mcp.tool()
async def get_internal_content(url: List[str]) -> str:
    """
    Tool is used for fetching content from a given URL.
    
    This tool retrieves the full text content from a specified web page URL. It is designed to be 
    used after the initial web search to gather more detailed information from specific pages.
    
    Args:
        list urls (str): The URL of the web page from which to fetch content.
    Returns:
        str: The full text content of the specified web page.
    
    Raises:
        Exception: If an error occurs while fetching the web page.
    
    Example:
        get_internal_content("https://example.com")
        # Returns the full text content from the specified URL.
    """
    try:
        results = await crawler2.scrape_multiple_urls(urls=url)
        return results
    except Exception as e:
            return f"Error during execution: {str(e)}"
server = Server(tools=[get_content, get_internal_content], mcp=mcp)
server.run()

if __name__ == "__main__":
    mcp.run(transport="http", port=9000,host="localhost", debug=True)
