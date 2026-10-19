import os
import stripe
from fastapi import FastAPI, Request, HTTPException, Header
from motor.motor_asyncio import AsyncIOMotorClient

# Initialize FastAPI app
app = FastAPI(title="Jesse Autopilot Bridge")

# ------------------------------------------------------------------------------
# 1. Environment Variables & Stripe Setup
# ------------------------------------------------------------------------------
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
SELLVIA_WEBHOOK_SECRET = os.getenv("SELLVIA_WEBHOOK_SECRET")
SELLVIA_MASTER_KEY = os.getenv("SELLVIA_MASTER_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ------------------------------------------------------------------------------
# 2. Asynchronous MongoDB Client (Motor)
# ------------------------------------------------------------------------------
# Fallback to local or None if MONGODB_URI is not set during initial builds
db = None
if MONGODB_URI:
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client["autopilot_store"]  # Main database instance

# ------------------------------------------------------------------------------
# 3. Healthcheck Endpoint
# ------------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "jesse-autopilot-bridge",
        "mongodb_connected": db is not None
    }

# ------------------------------------------------------------------------------
# 4. Stripe Webhook Endpoint (With Async MongoDB Logging)
# ------------------------------------------------------------------------------
@app.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()

    # Validate Stripe Signature if secret is present
    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Fallback to raw JSON reading if secret verification is skipped in dev
        event = await request.json()

    # Log incoming webhook payload directly into MongoDB
    if db is not None:
        await db["stripe_events"].insert_one({
            "event_type": event.get("type"),
            "event_id": event.get("id"),
            "data": event,
            "status": "received"
        })

    # Business Logic for Completed Orders
    event_type = event.get("type")
    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        
        # Save customer order specifically into 'orders' collection
        if db is not None:
            await db["orders"].insert_one({
                "checkout_session_id": session.get("id"),
                "customer_email": session.get("customer_details", {}).get("email"),
                "amount_total": session.get("amount_total"),
                "currency": session.get("currency"),
                "payment_status": session.get("payment_status"),
                "shipping_details": session.get("shipping_details")
            })

    return {"status": "success"}

# ------------------------------------------------------------------------------
# 5. Sellvia Webhook Endpoint (For Status / Order Updates)
# ------------------------------------------------------------------------------
@app.post("/sellvia-webhook")
async def sellvia_webhook(request: Request):
    payload = await request.json()

    # Log Sellvia tracking and fulfillment updates to MongoDB
    if db is not None:
        await db["sellvia_events"].insert_one({
            "payload": payload,
            "type": payload.get("event") or "status_update"
        })

    return {"status": "success"}
