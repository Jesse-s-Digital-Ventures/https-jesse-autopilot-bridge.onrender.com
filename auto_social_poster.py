import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from openai import OpenAI
import anthropic

# -------------------------------------------------------------------
# 1. Configuration & Credentials
# -------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")

STORE_RSS_URL = os.getenv(
    "STORE_RSS_URL", 
    "https://wonderfulgemspoint.shop/collections/all.atom"
)

# Initialize AI Clients
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


# -------------------------------------------------------------------
# 2. RSS Feed Parser (Past 24 Hours)
# -------------------------------------------------------------------
def fetch_recent_products(feed_url):
    print(f"[INFO] Fetching product feed from {feed_url}...")
    try:
        response = requests.get(feed_url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to download RSS feed: {e}")
        return []

    products = []
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(days=1)

    try:
        root = ET.fromstring(response.content)
        # Atom feeds (Shopify default format) use the standard Atom namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        for entry in root.findall('atom:entry', ns):
            pub_elem = entry.find('atom:published', ns)
            if pub_elem is None or not pub_elem.text:
                continue

            published_dt = datetime.fromisoformat(pub_elem.text.replace('Z', '+00:00'))

            if published_dt >= cutoff_time:
                title = entry.find('atom:title', ns).text
                link_elem = entry.find('atom:link', ns)
                link = link_elem.attrib.get('href') if link_elem is not None else ""

                # Extract product image URL from HTML summary block
                summary_elem = entry.find('atom:summary', ns)
                image_url = None
                if summary_elem is not None and summary_elem.text and 'src="' in summary_elem.text:
                    image_url = summary_elem.text.split('src="')[1].split('"')[0]

                products.append({
                    'title': title,
                    'link': link,
                    'image_url': image_url,
                    'published': published_dt
                })

    except Exception as e:
        print(f"[ERROR] XML Feed Parsing Error: {e}")

    print(f"[INFO] Discovered {len(products)} new product(s) published in the past 24 hours.")
    return products


# -------------------------------------------------------------------
# 3. AI Copy Generation (OpenAI & Anthropic Claude)
# -------------------------------------------------------------------
def generate_captions(product_title, product_link):
    """Generates promotional copy using OpenAI and Claude."""
    prompt = (
        f"Write an engaging, high-converting social media caption for product: '{product_title}'. "
        f"Brand: Wonderful Gems Point. Include 3-5 relevant hashtags and CTA link: {product_link}. "
        "Keep it concise, stylish, and engaging."
    )

    # A. OpenAI Generation
    openai_caption = None
    if openai_client:
        try:
            res = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            openai_caption = res.choices[0].message.content.strip()
            print("[SUCCESS] Generated caption using OpenAI.")
        except Exception as e:
            print(f"[ERROR] OpenAI generation error: {e}")

    # B. Claude (Anthropic) Generation
    claude_caption = None
    if anthropic_client:
        try:
            res = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            claude_caption = res.content[0].text.strip()
            print("[SUCCESS] Generated caption using Claude.")
        except Exception as e:
            print(f"[ERROR] Claude generation error: {e}")

    # Fallback default if API calls are skipped/failed
    default_caption = f"Check out our new item: {product_title}! Shop now: {product_link} #WonderfulGemsPoint #Jewelry"
    
    # Return selected versions for platforms (combining or assigning as desired)
    meta_caption = openai_caption or default_caption
    tiktok_caption = claude_caption or openai_caption or default_caption

    return meta_caption, tiktok_caption


# -------------------------------------------------------------------
# 4. Social Media Direct Posting Endpoints
# -------------------------------------------------------------------
def post_to_facebook(page_id, token, caption, image_url):
    if not page_id or not token:
        print("[SKIP] Facebook credentials missing.")
        return

    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    payload = {'message': caption, 'url': image_url, 'access_token': token}
    res = requests.post(url, data=payload)
    
    if res.status_code == 200:
        print(f"[SUCCESS] Posted to Facebook Page! ID: {res.json().get('id')}")
    else:
        print(f"[ERROR] Facebook publishing failed: {res.text}")


def post_to_instagram(ig_id, token, caption, image_url):
    if not ig_id or not token or not image_url:
        print("[SKIP] Instagram credentials or image missing.")
        return

    # Container Creation Phase
    create_url = f"https://graph.facebook.com/v19.0/{ig_id}/media"
    create_payload = {'image_url': image_url, 'caption': caption, 'access_token': token}
    res = requests.post(create_url, data=create_payload)
    
    if res.status_code != 200:
        print(f"[ERROR] Instagram Container creation failed: {res.text}")
        return

    creation_id = res.json().get('id')
    time.sleep(5)  # Wait for media container status check

    # Media Publish Phase
    pub_url = f"https://graph.facebook.com/v19.0/{ig_id}/media_publish"
    pub_payload = {'creation_id': creation_id, 'access_token': token}
    pub_res = requests.post(pub_url, data=pub_payload)
    
    if pub_res.status_code == 200:
        print(f"[SUCCESS] Posted to Instagram! Media ID: {pub_res.json().get('id')}")
    else:
        print(f"[ERROR] Instagram publishing failed: {pub_res.text}")


def post_to_tiktok(token, caption, image_url):
    if not token or not image_url:
        print("[SKIP] TikTok token or image missing.")
        return

    url = "https://open.tiktokapis.com/v2/post/publish/content/init/"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json; charset=UTF-8'
    }
    payload = {
        "post_info": {
            "title": caption,
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_comment": False
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": 1,
            "photo_images": [image_url]
        },
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO"
    }

    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        print(f"[SUCCESS] Posted photo to TikTok! Share ID: {res.json().get('data', {}).get('publish_id')}")
    else:
        print(f"[ERROR] TikTok publishing failed: {res.text}")


# -------------------------------------------------------------------
# 5. Main Execution Flow
# -------------------------------------------------------------------
def main():
    print("=== Launching Daily Social Media Cron Job ===")
    products = fetch_recent_products(STORE_RSS_URL)

    if not products:
        print("[INFO] No new items posted in the past 24 hours. Exiting process.")
        return

    for item in products:
        print(f"\n--- Processing Product: {item['title']} ---")
        meta_caption, tiktok_caption = generate_captions(item['title'], item['link'])
        image_url = item['image_url']

        # Publish content across active endpoints
        post_to_facebook(FACEBOOK_PAGE_ID, META_PAGE_ACCESS_TOKEN, meta_caption, image_url)
        post_to_instagram(INSTAGRAM_ACCOUNT_ID, META_PAGE_ACCESS_TOKEN, meta_caption, image_url)
        post_to_tiktok(TIKTOK_ACCESS_TOKEN, tiktok_caption, image_url)

    print("\n=== Cron Execution Finished ===")


if __name__ == "__main__":
    main()

