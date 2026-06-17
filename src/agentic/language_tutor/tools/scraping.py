# src/agentic/language_tutor/tools/scraping.py
import os
import requests
from bs4 import BeautifulSoup

def get_raw_html(url: str) -> str:
    """Fetches text payload streams out of external network web links."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def process_and_save_document(html_content: str, filename: str, category_path: str) -> dict:
    """Saves raw text as clear markdown and returns clean string content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    for noise in soup(["script", "style", "nav", "footer", "header", "aside"]):
        noise.extract()
    clean_text = soup.get_text(separator=' ', strip=True)
    
    base_refs = os.path.abspath(os.path.join(os.getcwd(), "..", "references"))
    target_dir = os.path.join(base_refs, category_path)
    os.makedirs(target_dir, exist_ok=True)
    
    full_path = os.path.join(target_dir, f"{filename.replace('.md', '')}.md")
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(clean_text) # Simplified frameworkless local serialization pass
        
    return {"file_path": full_path, "clean_text": clean_text}
