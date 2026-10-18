# src/agentic/language_tutor/tools/scraping.py
import requests
from bs4 import BeautifulSoup

# Import your newly centralized normalization engine directly
from .file_management import save_markdown_document

def get_raw_html(url: str) -> str:
    """Fetches text payload streams out of external network web links, strictly decoded in UTF-8."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    response.encoding = 'utf-8'
    return response.text

def process_and_save_document(html_content: str, filename: str, category_path: str) -> dict:
    """Saves raw text as beautifully structured markdown and returns clean string content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    markdown_lines = []

    # 🛠️ REAL FIX: Extract metadata FIRST while the complete HTML tag tree is intact
    title_element = soup.find('h1', id='title1') or soup.find('h1')
    author_element = soup.find('p', class_='author-name') or soup.find('div', class_='author-name') or soup.find(id='author1')
    role_element = soup.find('p', class_='author-role') or soup.find('div', class_='author-role') or soup.find(id='author2')

    if title_element:
        title_text = title_element.get_text().strip().replace('\xa0', ' ')
        markdown_lines.append(f"# {title_text}")
    
    if author_element:
        author_text = author_element.get_text().strip().replace('\xa0', ' ')
        if not author_text.lower().startswith('by'):
            author_text = f"By {author_text}"
        markdown_lines.append(f"### {author_text}")

    if role_element:
        role_text = role_element.get_text().strip().replace('\xa0', ' ')
        markdown_lines.append(f"### {role_text}")

    if markdown_lines:
        markdown_lines.append("")

    # Now it is safe to clean out layout noise tags from the document body
    for noise in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        noise.extract()

    # Extract core body container
    body_container = soup.find('div', class_='body-block') or soup.find('article') or soup
    
    body_lines = []
    for element in body_container.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'blockquote']):
        if element == title_element:
            continue
            
        text_content = element.get_text().strip()
        if not text_content:
            continue
            
        text_content = text_content.replace('\xa0', ' ')
        
        if element in [author_element, role_element]:
            continue

        if element.name == 'h1':
            body_lines.append(f"\n# {text_content}\n")
        elif element.name == 'h2':
            body_lines.append(f"\n## {text_content}\n")
        elif element.name == 'h3':
            body_lines.append(f"\n### {text_content}\n")
        elif element.name == 'p':
            if 'verse' in element.get('class', []):
                body_lines.append(f"> *{text_content}*")
            else:
                body_lines.append(f"\n{text_content}\n")
        elif element.name == 'li':
            body_lines.append(f"* {text_content}")
        elif element.name == 'blockquote':
            body_lines.append(f"\n> {text_content}\n")

    # Combine body text or use safe fallback, preserving your top headers
    if not body_lines:
        fallback_text = soup.get_text(separator='\n\n', strip=True)
        markdown_lines.append(fallback_text)
    else:
        markdown_lines.extend(body_lines)

    clean_markdown = "\n".join(markdown_lines).strip()
    
    # Offload file path resolution and disk writes to your centralized manager module
    full_path = save_markdown_document(
        content=clean_markdown,
        filename=filename,
        category_path=category_path
    )
        
    return {"file_path": full_path, "clean_text": clean_markdown}
