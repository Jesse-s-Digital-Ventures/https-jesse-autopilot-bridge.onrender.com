import os
import time
import requests
import feedparser
from datetime import datetime, timedelta, timezone
import openai
import anthropic

# ==========================================
# CONFIGURATION & API KEYS
# ==========================================
RSS_FEED_URL = "https://fabulousgemsparlor.shop/collections/all.atom"

# Securely retrieve API keys from environment variables
AYRSHARE_API_KEY = os.getenv("AYRSHARE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ==========================================
# 1. FETCH RECENT PRODUCTS FROM RSS
# ==========================================
def get_recent_products(feed_url, hours=24):
    """Parse RSS feed and return products updated/published in the past X hours."""
    print(f"[1/4] Fetching RSS feed from: {feed_url}...")
    feed = feedparser.parse(feed_url)
    
    recent_products = []
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    for entry in feed.entries:
        # Parse published or updated timestamp
        published_parsed = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
        if published_parsed:
            entry_time = datetime.fromtimestamp(time.mktime(published_parsed), tz=timezone.utc)
            if entry_time >= cutoff_time:
                # Extract image URL from Atom link/media tags if present
                image_url = None
                if 'links' in entry:
                    for link in entry.links:
                        if link.get('type', '').startswith('image/'):
                            image_url = link.get('href')
                            break
                
                recent_products.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary', ''),
                    'image_url': image_url,
                    'updated': entry_time
                })

    print(f"Found {len(recent_products)} products updated in the last {hours} hours.")
    return recent_products

# ==========================================
# 2. GENERATE COPY USING OPENAI (GPT-4o)
# ==========================================
def generate_openai_caption(product):
    """Generate high-converting caption using OpenAI."""
    print("  -> Generating caption with OpenAI (GPT-4o)...")
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    prompt = f"""
    Write an engaging, high-converting social media post for a gemstone jewelry product:
    Title: {product['title']}
    Link: {product['link']}
    
    Requirements:
    - Target platforms: Facebook & Instagram
    - Include 3-5 relevant jewelry/fashion hashtags
    - Include a clear Call to Action driving clicks to the product link
    - Concise, modern, and exciting tone
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250
    )
    return response.choices[0].message.content.strip()

# ==========================================
# 3. GENERATE COPY USING CLAUDE (3.5 SONNET)
# ==========================================
def generate_claude_caption(product):
    """Generate high-converting script/caption using Anthropic Claude."""
    print("  -> Generating script with Claude 3.5 Sonnet...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""
    Write a short, punchy TikTok video script / caption for a gemstone jewelry product:
    Title: {product['title']}
    Link: {product['link']}
    
    Requirements:
    - Catchy hook in sentence 1
    - Highlight elegance, stone quality, and lifestyle appeal
    - Include top trending jewelry hashtags
    """
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()

# ==========================================
# 4. PUBLISH TO SOCIAL MEDIA VIA AYRSHARE
# ==========================================
def publish_to_ayrshare(post_text, platforms, media_url=None):
    """Send post payload to Ayrshare API endpoint."""
    print(f"[3/4] Publishing post to {', '.join(platforms)} via Ayrshare...")
    
    url = "https://app.ayrshare.com/api/post"
    headers = {
        "Authorization": f"Bearer {AYRSHARE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "post": post_text,
        "platforms": platforms
    }
    
    if media_url:
        payload["mediaUrls"] = [media_url]

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("Successfully published!")
        print(f"Post IDs: {result.get('id', 'N/A')}")
        return result
    else:
        print(f"Failed to publish. Status: {response.status_code}")
        print(f"Error detail: {response.text}")
        return None

# ==========================================
# MAIN EXECUTION WORKFLOW
# ==========================================
def main():
    # Step 1: Get recent products from the past 24 hours
    products = get_recent_products(RSS_FEED_URL, hours=24)
    
    if not products:
        print("No new products found in the RSS feed within the last 24 hours. Exiting workflow.")
        return

    # Step 2: Loop through products and generate/post social content
    for idx, product in enumerate(products, 1):
        print(f"\n--- Processing Product {idx}/{len(products)}: {product['title']} ---")
        
        # Choice A: Generate main caption with OpenAI for FB & IG
        fb_ig_caption = generate_openai_caption(product)
        
        # Choice B: Generate script with Claude for TikTok
        tiktok_caption = generate_claude_caption(product)
        
        # Step 3: Publish to Facebook & Instagram
        publish_to_ayrshare(
            post_text=fb_ig_caption, 
            platforms=["facebook", "instagram"], 
            media_url=product['image_url']
        )
        
        # Step 4: Publish to TikTok
        publish_to_ayrshare(
            post_text=tiktok_caption, 
            platforms=["tiktok"], 
            media_url=product['image_url']
        )

if __name__ == "__main__":
    main()
