import os
import feedparser
from fastapi import FastAPI, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
import anthropic

app = FastAPI(
    title="Jesse-Autopilot-Bridge",
    description="Automated social marketing bridge for Wonderful Gems",
    version="1.0.0",
)

#------------------------------------------------------------------------------
# Wise Webhook & Root Health Endpoints
# ------------------------------------------------------------------------------
@app.get("/")
def health():
    return {"message": "Jesse Autopilot Bridge Active"}

@app.post("/api/wise/webhook")
async def wise_webhook(request: Request):
    try:
        data = await request.json()
        print("Wise Webhook Received:", data)
    except Exception as e:
        print("Wise Webhook ping received (empty or non-JSON body)")
    
    # Return 200 OK immediately so Wise verification succeeds
    return {"status": "success", "received": True}
 ------------------------------------------------------------------------------
# Environment Variables
# ------------------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
SELLVIA_RSS_URL = os.getenv("SELLVIA_RSS_URL", "https://fabulousgemsparlor.store/rss")

# ------------------------------------------------------------------------------
# Database Connection
# ------------------------------------------------------------------------------
db_client = None
if MONGODB_URI:
    try:
        db_client = AsyncIOMotorClient(MONGODB_URI)
        db = db_client.get_default_database()
    except Exception as e:
        print(f"MongoDB Connection Warning: {e}")

# ------------------------------------------------------------------------------
# Health Check Endpoint
# ------------------------------------------------------------------------------
@app.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check():
    mongo_status = False
    if db_client:
        try:
            await db_client.admin.command("ping")
            mongo_status = True
        except Exception:
            mongo_status = False

    return {
        "status": "healthy",
        "service": "jesse-autopilot-bridge",
        "mongodb_connected": mongo_status,
    }

# ------------------------------------------------------------------------------
# Auto-Posting Trigger Route
#------------------------------------------------------------------------------
@app.post("/cron/rss-post", status_code=status.HTTP_200_OK)
async def trigger_rss_post():
    # 1. Fetch products from Sellvia RSS feed
    try:
        feed = feedparser.parse(SELLVIA_RSS_URL)
        if not feed.entries:
            raise HTTPException(
                status_code=404, detail="No entries found in RSS feed."
            )
        latest_item = feed.entries[0]
        title = getattr(latest_item, "title", "Gemstone Product")
        link = getattr(latest_item, "link", SELLVIA_RSS_URL)
        description = getattr(latest_item, "summary", title)
    except Exception as err:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch RSS feed: {str(err)}"
        )

    # 2. Generate marketing copy with OpenAI / Claude
    caption = ""
    if ANTHROPIC_API_KEY:
        try:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": f"Write an engaging short social media post for Instagram/TikTok promoting this product: {title}. Description: {description}. Include 3 trending hashtags and a call-to-action.",
                    }
                ],
            )
            caption = message.content[0].text
        except Exception as e:
            print(f"Claude API failed, falling back: {e}")

    if not caption and OPENAI_API_KEY:
        try:
            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a social media manager for a jewelry store.",
                    },
                    {
                        "role": "user",
                        "content": f"Write a promotional social media post for: {title}. Link: {link}",
                    },
                ],
            )
            caption = response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API failed: {e}")

    if not caption:
        caption = f"Check out our latest gemstone release: {title}! Shop now: {link} #gemstones #jewelry"

    # 3. Log to MongoDB if connected
    if db_client:
        try:
            posts_col = db["posts_log"]
            await posts_col.insert_one(
                {
                    "title": title,
                    "link": link,
                    "caption": caption,
                    "status": "queued",
                }
            )
        except Exception as e:
            print(f"Database logging warning: {e}")

    return {
        "status": "success",
        "product": title,
        "product_link": link,
        "generated_caption": caption,
    }
