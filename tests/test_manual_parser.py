
import requests
import re
import html

def parse_ddg_html():
    url = "https://html.duckduckgo.com/html/"
    data = {"q": "python programming"}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    print(f"Requesting {url}...")
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=10)
        content = resp.text
        
        # Regex to find results
        # Pattern: <a class="result__a" href="(url)">(title)</a>
        # Note: HTML might have attributes in different order or extra spaces.
        
        pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, content)
        
        print(f"Found {len(matches)} matches")
        
        results = []
        for url, title_html in matches:
            title = html.unescape(re.sub(r'<[^>]+>', '', title_html)).strip()
            # DDG url might be wrapped in /l/?kh=-1&uddg=...
            # But usually it's the specific redirector.
            # Let's decode if needed or just return as is.
            # Actually DDG html uses absolute URLs often or relative redirect.
            
            results.append({"title": title, "href": url})
            
        return results[:5]

    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    results = parse_ddg_html()
    for r in results:
        print(f"- {r['title']}: {r['href']}")
