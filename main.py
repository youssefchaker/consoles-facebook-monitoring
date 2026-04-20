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
CONTENT_FILE = "seen_content.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

def load_json_data(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f: return set(json.load(f))
        except: return set()
    return set()

def save_json_data(filename, data_set):
    with open(filename, "w", encoding="utf-8") as f: json.dump(list(data_set), f)

def clean_fb_url(url):
    if not url: return None
    # Marketplace normalization
    if "/commerce/listing/" in url:
        match = re.search(r"listing/(\d+)", url)
        return f"https://www.facebook.com/commerce/listing/{match.group(1)}/" if match else url.split('?')[0]
    # Photo normalization (fbid is the constant across groups)
    if "/photo" in url:
        match = re.search(r"fbid=(\d+)", url)
        return f"https://www.facebook.com/photo/?fbid={match.group(1)}" if match else url.split('&')[0]
    # Strip tracking parameters from permalinks
    return url.split('?')[0].rstrip('/')

async def run_monitor():
    seen_posts = load_json_data(DATA_FILE)
    seen_content = load_json_data(CONTENT_FILE)
    
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
                    await page.goto(f"{group_url}?sorting_setting=CHRONOLOGICAL", wait_until="commit")
                    
                    try:
                        # Wait for the feed to hydrate
                        await page.wait_for_selector('div[aria-posinset]', timeout=10000)
                    except:
                        continue

                    # Small nudge to load lazy elements
                    await page.mouse.wheel(0, 500)
                    await asyncio.sleep(1)

                    post_containers = await page.query_selector_all('div[aria-posinset]')
                    targets = post_containers[:15] # Focus on the newest entries

                    for container in targets:
                        # 1. Link Extraction
                        link_elem = await container.query_selector('a[href*="/posts/"], a[href*="/permalink/"], a[href*="/commerce/listing/"], a[href*="/photo/"]')
                        if not link_elem: continue
                        
                        raw_url = await link_elem.get_attribute("href")
                        if raw_url and raw_url.startswith('/'): 
                            raw_url = f"https://www.facebook.com{raw_url}"
                        
                        post_url = clean_fb_url(raw_url)

                        # 2. User & Message Extraction for Fingerprinting
                        user_elem = await container.query_selector('h2 a, h3 a, strong a')
                        user = (await user_elem.inner_text()).strip() if user_elem else "Unknown"
                        
                        msg_elem = await container.query_selector('div[data-ad-comet-preview="message"]')
                        msg_text = (await msg_elem.inner_text()).strip()[:50] if msg_elem else "NO_TEXT"

                        content_fingerprint = f"{user}_{msg_text}"

                        # 3. Duplicate and Cross-Post Check
                        if post_url not in seen_posts and content_fingerprint not in seen_content:
                            
                            # DISPLAY DATA
                            print("-" * 50)
                            print(f"NEW POST DETECTED")
                            print(f"USER: {user}")
                            print(f"TEXT: {msg_text}...")
                            print(f"URL:  {post_url}")
                            
                            winsound.Beep(1000, 500) 
                            webbrowser.open(post_url)

                            # Record to prevent future duplicates
                            seen_posts.add(post_url)
                            seen_content.add(content_fingerprint)
                            
                            save_json_data(DATA_FILE, seen_posts)
                            save_json_data(CONTENT_FILE, seen_content)

                except Exception as e:
                    print(f"[!] Error on group scan: {e}")
            
            # Randomized wait to mimic human behavior
            wait_time = CHECK_INTERVAL + random.randint(-15, 30)
            print(f"\nCycle finished. Resting {wait_time}s...")
            await asyncio.sleep(wait_time)

if __name__ == "__main__":
    try:
        asyncio.run(run_monitor())
    except KeyboardInterrupt:
        print("\nMonitor stopped by user.")