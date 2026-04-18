import requests
from bs4 import BeautifulSoup
from smolagents import tool

@tool
def web_scraper(url: str) -> str:
    """
    Fetches raw text from a URL and cleans it by removing HTML tags, scripts, and styles.
    Args:
        url: The web address of the story or article to scrape.
    """
    try:
        # User-agent header makes the request look like it's coming from a browser
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove "noise" elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.extract()
            
        # Get text and clean up whitespace
        text = soup.get_text(separator=' ')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return clean_text
    except Exception as e:
        return f"Failed to scrape the URL: {str(e)}"
