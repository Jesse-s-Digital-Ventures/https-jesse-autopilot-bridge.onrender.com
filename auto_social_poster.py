import os
import re
import time
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from openai import OpenAI
import anthropic

# ==============================================================================
# CONFIGURATION & API KEYS
# ==============================================================================
STORE_RSS_URL = "https://wonderfulgemspoint.shop/collections/all.atom"

# AI Clients
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Meta / Facebook & Instagram Graph API
META_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")

# TikTok Content Posting API
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")

# Initialize AI SDKs
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# ==============================================================================
# 1. FETCH PRODUCTS FROM RSS FEED (LAST 24 HOURS)
# ==============================================================================
def get_recent_products(feed_url: str, hours: int = 24) -> list:
    """Parses the Shopify Atom RSS feed for products added/updated in the past 24h."""
    feed = feedparser.parse(feed_url)
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_products = []

    for entry in feed.entries:
        # Parse published/updated date
        pub_tuple = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        if not pub_tuple:
            continue
        
        pub_datetime = datetime(*pub_tuple[:6], tzinfo=timezone.utc)
        
        if pub_datetime >= cutoff_time:
            # Extract image URL from HTML summary if available
            image_match = re.search(r'src="(https://[^"]+)"', entry.summary)
            image_url = image_match.group(1) if image_match else None

            # Clean raw summary HTML to plain text
            clean_summary = re.sub(r'<[^>]+>', '', entry.summary).strip()

            recent_products.append({
                "title": entry.title,
                "link": entry.link,
                "summary": clean_summary[:500],
                "image_url": image_url,
                "published_at": pub_datetime.isoformat()
            })

    return recent_products

# ==============================================================================
# 2. AI COPY GENERATION (OPENAI / CLAUDE)
# ==============================================================================
def generate_copy_openai(product: dict) -> dict:
    """Generates tailored captions for FB, IG, and TikTok using OpenAI (GPT-4o)."""
    prompt = f"""
    You are an e-commerce social media manager for 'Wonderful Gems Point'.
    Write tailored social media captions for this product:
    
    Title: {product['title']}
    Description: {product['summary']}
    Product Link: {product['link']}

    Return strictly a JSON-like formatted response with three fields:
    - INSTAGRAM: An aesthetic caption with 5 niche hashtags and a call-to-action.
    - FACEBOOK: A friendly, engaging post highlighting benefits with the link.
    - TIKTOK: A catchy 1-2 sentence viral video/carousel hook script.
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    content = response.choices[0].message.content
    return parse_ai_response(content)

def generate_copy_claude(product: dict) -> dict:
    """Alternative copy generator using Anthropic Claude (Claude 3.5 Sonnet)."""
    response = anthropic_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"Write captions for FB, IG, and TikTok for this item:\nTitle: {product['title']}\nLink: {product['link']}"
        }]
    )
    return {"FACEBOOK": response.content[0].text, "INSTAGRAM": "", "TIKTOK": ""}

def parse_ai_response(text: str) -> dict:
    """Helper parser to split captions per platform."""
    return {
        "instagram": text,  # Can refine with regex/json schema matching
        "facebook": text,
        "tiktok": text
    }

# ==============================================================================
# 3. PUBLISHING API MODULES
# ==============================================================================
def post_to_facebook(image_url: str, caption: str) -> bool:
    """Publishes a photo post to a Facebook Page via Graph API."""
    if not META_ACCESS_TOKEN or not FACEBOOK_PAGE_ID:
        print("[FB] Missing Meta Credentials. Skipping Facebook upload.")
        return False

    url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/photos"
    payload = {
        "url": image_url,
        "message": caption,
        "access_token": META_ACCESS_TOKEN
    }
    res = requests.post(url, data=payload)
    if res.status_code == 200:
        print(f"[FB] Success! Post ID: {res.json().get('id')}")
        return True
    print(f"[FB] Error: {res.text}")
    return False

def post_to_instagram(image_url: str, caption: str) -> bool:
    """Publishes a photo post to an Instagram Business account via Graph API."""
    if not META_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        print("[IG] Missing Meta Credentials. Skipping Instagram upload.")
        return False

    # Step A: Create Media Container
    container_url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_ACCOUNT_ID}/media"
    container_payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": META_ACCESS_TOKEN
    }
    res = requests.post(container_url, data=container_payload)
    if res.status_code != 200:
        print(f"[IG] Container Creation Failed: {res.text}")
        return False
    
    creation_id = res.json().get("id")

    # Step B: Publish Media Container
    time.sleep(5)  # Wait for IG image processing
    publish_url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": META_ACCESS_TOKEN
    }
    pub_res = requests.post(publish_url, data=publish_payload)
    if pub_res.status_code == 200:
        print(f"[IG] Success! Published ID: {pub_res.json().get('id')}")
        return True
    print(f"[IG] Publishing Error: {pub_res.text}")
    return False

def post_to_tiktok(image_url: str, caption: str) -> bool:
    """Publishes a photo post to TikTok using the Direct Post Content API."""
    if not TIKTOK_ACCESS_TOKEN:
        print("[TikTok] Missing Token. Skipping TikTok upload.")
        return False

    url = "https://open.tiktokapis.com/v2/post/publish/content/init/"
    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "post_info": {
            "title": caption[:150],  # TikTok title character limit
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_comment": False,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": 1,
            "photo_images": [image_url]
        },
        "post_mode": "MEDIA_UPLOAD",
        "media_type": "PHOTO"
    }
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        print("[TikTok] Photo post successfully initiated!")
        return True
    print(f"[TikTok] Error: {res.text}")
    return False

# ==============================================================================
# MAIN EXECUTION FLOW
# ==============================================================================
def main():
    print("--- Checking Feed for Past 24h Products ---")
    products = get_recent_products(STORE_RSS_URL, hours=24)
    
    if not products:
        print("No new products published in the past day.")
        return

    print(f"Found {len(products)} new product(s) to publish.\n")

    for prod in products:
        print(f"Processing: {prod['title']}")

        # 1. Generate Copy via AI
        if openai_client:
            copy = generate_copy_openai(prod)
        elif anthropic_client:
            copy = generate_copy_claude(prod)
        else:
            print("No AI credentials found. Using fallback RSS copy.")
            copy = {"facebook": prod["summary"], "instagram": prod["summary"], "tiktok": prod["title"]}

        # 2. Publish Across Social Accounts
        if prod["image_url"]:
            post_to_facebook(prod["image_url"], copy["facebook"])
            post_to_instagram(prod["image_url"], copy["instagram"])
            post_to_tiktok(prod["image_url"], copy["tiktok"])
        else:
            print("Skipping media posts: Product entry lacks an image URL.")

if __name__ == "__main__":
    main()
