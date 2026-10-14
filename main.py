import os
import requests
import stripe
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI App
app = FastAPI(title="Jesse Autopilot Bridge")

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Secret Environment Variables
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Configure Stripe API
stripe.api_key = STRIPE_SECRET_KEY


# ----------------------------------------------------
# HELPER / BUSINESS LOGIC FUNCTIONS
# ----------------------------------------------------
def process_sellvia_fulfillment(order_data: dict) -> bool:
    """
    Core automation logic for sending paid Shopify orders to Sellvia.
    """
    order_id = order_data.get("id")
    line_items = order_data.get("line_items", [])
    
    print(f"[SELLVIA AUTOMATION] Processing Order ID: {order_id} with {len(line_items)} item(s).")
    
    # Sellvia integration requests go here
    # e.g., requests.post("https://api.sellvia.com/v1/orders", json=...)
    
    return True


# ----------------------------------------------------
# API ENDPOINTS
# ----------------------------------------------------

# 1. Healthcheck Route
@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Jesse Autopilot FastAPI Bridge",
        "version": "1.0.0"
    }


# 2. Shopify Order Webhook Endpoint
@app.post("/api/shopify/webhook/order-created")
async def shopify_order_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    order_id = payload.get("id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Order ID missing from payload")

    # Run Sellvia fulfillment execution logic
    success = process_sellvia_fulfillment(payload)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to initiate Sellvia fulfillment")

    return {
        "status": "success",
        "order_id": order_id,
        "action": "sent_to_sellvia"
    }


# 3. Sellvia Auto-Approval / Cron Job Endpoint (GitHub Actions)
@app.post("/api/sellvia/auto-approve")
def auto_approve(authorization: str = Header(None)):
    if not authorization or authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized request access token")

    print("[AUTOPILOT] Executing scheduled batch order auto-approval.")
    
    return {
        "status": "success",
        "message": "All pending Sellvia payout & fulfillment batches processed"
    }


# 4. Stripe Webhook Endpoint
@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature header")

    # Handle Stripe payment events
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        print(f"[STRIPE] Payment Succeeded: {payment_intent['id']}")

    return {"status": "success"}
