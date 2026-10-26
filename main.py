import os
import asyncio
import feedparser
import httpx
from fastapi import FastAPI, HTTPException, Request, status, Header
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
import anthropic

app = FastAPI(
    title="Jesse-Autopilot-Bridge",
    description="Automated social marketing bridge for Wonderful Gems",
    version="1.1.0",
)

# ------------------------------------------------------------------------------
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
    except Exception:
        print("Wise Webhook ping received (empty or non-JSON body)")
    return {"status": "success", "received": True}

# ------------------------------------------------------------------------------
# Environment Variables
# ------------------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
SELLVIA_RSS_URL = os.getenv("SELLVIA_RSS_URL", "https://fabulousgemsparlor.store/rss")
CRON_SECRET = os.getenv("CRON_SECRET", "")

# Tunables for "more time and room"
RSS_HTTP_TIMEOUT_SECONDS = float(os.getenv("RSS_HTTP_TIMEOUT_SECONDS", "20"))
MODEL_TIMEOUT_SECONDS = float(os.getenv("MODEL_TIMEOUT_SECONDS", "45"))
MAX_DESCRIPTION_CHARS = int(os.getenv("MAX_DESCRIPTION_CHARS", "1200"))
MAX_CAPTION_CHARS = int(os.getenv("MAX_CAPTION_CHARS", "500"))

# ------------------------------------------------------------------------------
# Database Connection
# ------------------------------------------------------------------------------
db_client = None
db = None
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
# Helper functions
# ------------------------------------------------------------------------------
async def fetch_latest_rss_item(url: str):
    """
    Fetch RSS over HTTP with explicit timeout and parse result.
    Raises HTTPException with meaningful status codes.
    """
    timeout = httpx.Timeout(RSS_HTTP_TIMEOUT_SECONDS, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers={"User-Agent": "JesseAutopilotBridge/1.1"})
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"RSS upstream returned {e.response.status_code} for {url}",
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail=f"Timed out fetching RSS feed after {RSS_HTTP_TIMEOUT_SECONDS}s",
            )
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch RSS feed: {str(e)}")

    feed = feedparser.parse(response.text)
    if not feed.entries:
        raise HTTPException(status_code=404, detail="No entries found in RSS feed.")

    latest_item = feed.entries[0]
    title = getattr(latest_item, "title", "Gemstone Product")
    link = getattr(latest_item, "link", url)
    description = getattr(latest_item, "summary", title) or title
    description = description[:MAX_DESCRIPTION_CHARS]
    return title, link, description


async def generate_caption_with_claude(title: str, description: str) -> str:
    """
    Run blocking Anthropic SDK in a thread with timeout to avoid blocking event loop.
    """
    if not ANTHROPIC_API_KEY:
        return ""

    def _blocking_call() -> str:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write an engaging short social media post for Instagram/TikTok "
                        f"promoting this product: {title}. Description: {description}. "
                        "Include 3 relevant hashtags and a call-to-action. Keep it concise."
                    ),
                }
            ],
        )
        text = ""
        try:
            text = message.content[0].text
        except Exception:
            text = ""
        return text or ""

    try:
        return await asyncio.wait_for(asyncio.to_thread(_blocking_call), timeout=MODEL_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        print(f"Claude timeout after {MODEL_TIMEOUT_SECONDS}s")
        return ""
    except Exception as e:
        print(f"Claude API failed, falling back: {e}")
        return ""


async def generate_caption_with_openai(title: str, link: str) -> str:
    if not OPENAI_API_KEY:
        return ""

    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=MODEL_TIMEOUT_SECONDS)
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a social media manager for a jewelry store.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Write a short promotional social media post for: {title}. "
                            f"Link: {link}. Include 3 relevant hashtags and CTA."
                        ),
                    },
                ],
            ),
            timeout=MODEL_TIMEOUT_SECONDS,
        )
        return (response.choices[0].message.content or "")
    except asyncio.TimeoutError:
        print(f"OpenAI timeout after {MODEL_TIMEOUT_SECONDS}s")
        return ""
    except Exception as e:
        print(f"OpenAI API failed: {e}")
        return ""


# ------------------------------------------------------------------------------
# Auto-Posting Trigger Route
# ------------------------------------------------------------------------------
@app.get("/cron/rss-post")
async def rss_post_get_hint():
    return {
        "status": "method_not_allowed",
        "message": "Use POST /cron/rss-post to trigger the job.",
    }


@app.post("/cron/rss-post", status_code=status.HTTP_200_OK)
async def trigger_rss_post(x_cron_secret: str | None = Header(default=None)):
    # Optional endpoint protection if CRON_SECRET is set
    if CRON_SECRET and x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized cron request")

    # 1) Fetch latest RSS item with explicit timeout and better upstream errors
    title, link, description = await fetch_latest_rss_item(SELLVIA_RSS_URL)

    # 2) Generate marketing copy with Claude, fallback to OpenAI, then fallback template
    caption = await generate_caption_with_claude(title, description)

    if not caption:
        caption = await generate_caption_with_openai(title, link)

    if not caption:
        caption = f"Check out our latest gemstone release: {title}! Shop now: {link} #gemstones #jewelry"

    caption = caption.strip()
    if len(caption) > MAX_CAPTION_CHARS:
        caption = caption[: MAX_CAPTION_CHARS - 1].rstrip() + "…"

    # 3) Log to MongoDB if connected
    if db_client and db is not None:
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
        "timeouts": {
            "rss_http_timeout_seconds": RSS_HTTP_TIMEOUT_SECONDS,
            "model_timeout_seconds": MODEL_TIMEOUT_SECONDS,
        },
    }
