import asyncio
import json
import os
import re
import random
import winsound
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
GROUPS = [
    "https://www.facebook.com/groups/518446061627766/",
    "https://www.facebook.com/groups/480020222841027/",
    "https://www.facebook.com/groups/2352430271473134/",
    "https://www.facebook.com/groups/636662911982778/",
    "https://www.facebook.com/groups/1047269889138806/",
    "https://www.facebook.com/groups/retrogamingtunisie/",
]

KEYWORDS = ["wii", "switch", "3ds", "vita", "psp"]
CHECK_INTERVAL = 150 
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

async def run_monitor():
    seen_posts = load_seen_posts()
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True, # Toggle to False for manual login
            user_agent=USER_AGENT
        )
        page = await context.new_page()

        # Quick check for login state
        await page.goto("https://www.facebook.com")
        if "login" in page.url:
            print("[!] Not logged in. Please run with headless=False once.")
            return

        print(f"[*] Monitor running. Checking {len(GROUPS)} groups for {KEYWORDS}...")

        while True:
            for group_url in GROUPS:
                try:
                    # Navigate directly to newest posts
                    await page.goto(f"{group_url}?sorting_setting=CHRONOLOGICAL", wait_until="domcontentloaded")
                    await page.wait_for_timeout(random.randint(3000, 5000))

                    posts = await page.query_selector_all('div[role="feed"] > div')

                    for post in posts:
                        text = (await post.inner_text()).lower()
                        
                        matches = [k for k in KEYWORDS if re.search(rf'{k}', text)]
                        
                        if matches:
                            link_elem = await post.query_selector('a[href*="/posts/"]')
                            raw_url = await link_elem.get_attribute("href") if link_elem else group_url
                            post_url = raw_url.split('?')[0]

                            if post_url not in seen_posts:
                                user_elem = await post.query_selector('h2 a, h3 a')
                                user = await user_elem.inner_text() if user_elem else "Unknown"
                                
                                # 1. PRINT TO TERMINAL
                                print("-" * 40)
                                print(f"MATCH: {matches}")
                                print(f"USER:  {user}")
                                print(f"URL:   {post_url}")
                                
                                winsound.Beep(1000, 500) 

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