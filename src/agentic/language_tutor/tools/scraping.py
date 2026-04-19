#tools/scraping.py

import os
import requests
from bs4 import BeautifulSoup
from smolagents import tool
from markdownify import markdownify as md
from .utils import get_git_root

@tool
def get_raw_html(url: str) -> str:
    """
    Fetches the raw HTML content from a URL to preserve structure for markdown conversion.
    Args:
        url: The web address to fetch.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text


@tool
def process_and_save_document(html_content: str, filename: str, category_path: str) -> dict:
    """
    Saves HTML as a .md file and returns clean text for sentence splitting.
    Returns a dictionary with 'file_path' and 'clean_text'.
    Args:
        html_content: The raw html content from a URL
        filename: The name of the md file to which the text will be extracted
        category_path: The path to the location (excluding file name) to where the file will be stored
    """
    # 1. Generate Clean Text for the Philologist
    soup = BeautifulSoup(html_content, 'html.parser')
    for noise in soup(["script", "style", "nav", "footer", "header", "aside"]):
        noise.extract()
    clean_text = soup.get_text(separator=' ', strip=True)

    # 2. Generate and Save Markdown for the Library
    markdown_text = md(html_content, heading_style="ATX")
    base_refs = os.path.abspath(os.path.join(os.getcwd(), "..", "references"))
    target_dir = os.path.join(base_refs, category_path)
    os.makedirs(target_dir, exist_ok=True)
    
    full_path = os.path.join(target_dir, f"{filename.replace('.md', '')}.md")
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    return {"file_path": full_path, "clean_text": clean_text}

