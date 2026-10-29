import os
import datetime
import requests
import feedparser
import openai
import anthropic

# 1. Configuration & Keys
STORE_RSS_URL = "https://fabulousgemsparlor.shop/collections/all.atom"  # Standard Shopify product feed
AYRSHARE_API_KEY = os.getenv("AYRSHARE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 2. Fetch RSS Feed and Filter for the Past 24 Hours
feed = feedparser.parse(STORE_RSS_URL)
now = datetime.datetime.now(datetime.timezone.utc)
one_day_ago = now - datetime.timedelta(days=1)

recent_products = []
for entry in feed.entries:
    # Shopify Atom feeds use updated_parsed or published_parsed
    published_time = datetime.datetime(*entry.published_parsed[:6], tzinfo=datetime.timezone.utc)
    if published_time >= one_day_ago:
        recent_products.append({
            "title": entry.title,
            "link": entry.link,
            "summary": entry.get("summary", "")
        })

print(f"Found {len(recent_products)} products added/updated in the past 24 hours.")

# 3. Generate Copy and Publish to Ayrshare
for product in recent_products:
    # Example draft prompt for OpenAI or Claude:
    prompt = f"Write a short, high-converting social media caption for Instagram, Facebook, and TikTok for this gemstone product: {product['title']}. Link: {product['link']}"
    
    # Generate copy with Anthropic Claude
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    post_text = response.content[0].text

    # Post via Ayrshare API
    ayrshare_headers = {
        "Authorization": f"Bearer {AYRSHARE_API_KEY}",
        "Content-Type": "application/json"
    }
    ayrshare_payload = {
        "post": post_text,
        "platforms": ["facebook", "instagram", "tiktok"]
    }
    
    res = requests.post("https://app.ayrshare.com/api/post", json=ayrshare_payload, headers=ayrshare_headers)
    print(f"Published '{product['title']}': {res.json()}")
