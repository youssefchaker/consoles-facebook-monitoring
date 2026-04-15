import asyncio
import json
import os
import random
import winsound
import webbrowser
import re
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
GROUPS = [
    "https://www.facebook.com/groups/518446061627766/",
    "https://www.facebook.com/groups/480020222841027/",
    "https://www.facebook.com/groups/2352430271473134/",
    "https://www.facebook.com/groups/636662911982778/",
    "https://www.facebook.com/groups/1047269889138806/"
]

CHECK_INTERVAL = 100 
SESSION_DIR = "./fb_session"
DATA_FILE = "seen_posts.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

def load_seen_posts():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return set(json.load(f))
        except: return set()
    return set()

def save_seen_posts(seen_set):
    with open(DATA_FILE, "w") as f: json.dump(list(seen_set), f)

def clean_fb_url(url):
    """
    Strips group-specific data to ensure the same post 
    shared in multiple groups is only detected once.
    """
    if not url: return None
    
    if "/commerce/listing/" in url:
        match = re.search(r"listing/(\d+)", url)
        if match:
            return f"https://www.facebook.com/commerce/listing/{match.group(1)}/"
        return url.split('?')[0].rstrip('/')

    if "/photo/" in url or "/photo.php" in url:
        match = re.search(r"fbid=(\d+)", url)
        if match:
            # We ignore the 'set=gm.123' part because that is group-specific
            return f"https://www.facebook.com/photo/?fbid={match.group(1)}"
        return url.split('&')[0]
    
    return url.split('?')[0].rstrip('/')

async def run_monitor():
    seen_posts = load_seen_posts()
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True,
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(60000)

        print(f"[*] Monitor active...")

        while True:
            for group_url in GROUPS:
                try:
                    await page.goto(f"{group_url}?sorting_setting=CHRONOLOGICAL", wait_until="domcontentloaded")
                    
                    try:
                        await page.wait_for_selector('div[role="feed"]', timeout=15000)
                    except:
                        continue
                    all_elements = await page.query_selector_all('div[role="feed"] > div')
                    posts = all_elements[:10] 

                    for post in posts:
                        link_elem = await post.query_selector(
                            'a[href*="/posts/"], a[href*="/permalink/"], a[href*="/photo/"], a[href*="/commerce/listing/"]'
                        )
                        
                        if not link_elem:
                            continue
                            
                        raw_url = await link_elem.get_attribute("href")
                        if raw_url and raw_url.startswith('/'):
                            raw_url = f"https://www.facebook.com{raw_url}"
                            
                        post_url = clean_fb_url(raw_url)

                        if post_url and post_url not in seen_posts:
                            user_elem = await post.query_selector('h2 a, h3 a, strong a')
                            user = await user_elem.inner_text() if user_elem else "Unknown Seller"
                            
                            print("-" * 40)
                            print(f"NEW POST | USER: {user}")
                            print(f"LINK: {post_url}")
                            
                            winsound.Beep(1000, 500) 
                            webbrowser.open(post_url)

                            seen_posts.add(post_url)
                            save_seen_posts(seen_posts)

                except Exception as e:
                    print(f"[!] Error: {e}")
            
            wait = CHECK_INTERVAL + random.randint(-20, 40)
            print(f"Cycle finished. Waiting {wait}s...")
            await asyncio.sleep(wait)

if __name__ == "__main__":
    try:
        asyncio.run(run_monitor())
    except KeyboardInterrupt:
        print("\nStopping...")