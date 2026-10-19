import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from langchain_core.documents import Document

def fetch_tn_schemes(list_url="https://www.tn.gov.in/scheme_list.php?dep_id=Mg==", limit=10):
    """
    Fetches schemes and scrapes detailed content for each.
    Set limit=None to scrape all 54 schemes.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print("Fetching scheme index page...")
    response = requests.get(list_url, headers=headers)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.content, "html.parser")
    
    scheme_items = []
    seen_titles = set()
    blacklist = {
        "important websites", "schemes", "home", "government", "departments", 
        "districts", "documents", "services", "news & events", "interact with govt", 
        "others", "csc login", "what's new", "skip to main content", "screen reader access"
    }

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"].strip()
        
        if not title or len(title) < 5 or title.lower() in blacklist:
            continue
            
        if "scheme_details.php" in href or ("scheme" in href and "id=" in href):
            if title not in seen_titles:
                seen_titles.add(title)
                full_url = urljoin(list_url, href)
                scheme_items.append((title, full_url))

    # Apply limit for testing/development
    to_scrape = scheme_items[:limit] if limit else scheme_items
    print(f"Found {len(scheme_items)} schemes. Fetching full details for {len(to_scrape)} schemes...")

    docs = []
    for title, url in to_scrape:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = res.apparent_encoding
            detail_soup = BeautifulSoup(res.content, "html.parser")
            
            # Extract main text body, stripping scripts and styles
            for elem in detail_soup(["script", "style", "nav", "footer", "header"]):
                elem.extract()
                
            main_content = detail_soup.find("table") or detail_soup.find("div", {"id": "content"}) or detail_soup.body
            clean_text = main_content.get_text(separator="\n", strip=True) if main_content else ""

            content = (
                f"Department: Agriculture - Farmers Welfare Department\n"
                f"Scheme Name: {title}\n"
                f"Source URL: {url}\n\n"
                f"Scheme Details:\n{clean_text}"
            )
            
            docs.append(Document(page_content=content, metadata={"source": url, "scheme": title}))
            print(f"  ✓ Fetched details: {title}")
        except Exception as e:
            print(f"  ✗ Failed to fetch {title}: {e}")

    return docs

if __name__ == "__main__":
    docs = fetch_tn_schemes(limit=3)  # Test with first 3 schemes
    if docs:
        print("\n--- Scraped Document Sample ---")
        print(docs[0].page_content[:400])