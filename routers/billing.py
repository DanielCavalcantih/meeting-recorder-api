import os
import stripe
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from supabase import create_client, Client

router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Initialize Supabase (with Service Role Key to bypass RLS and update profiles)
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client | None = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")

class CheckoutSessionRequest(BaseModel):
    plan_id: str
    user_id: str
    email: str

@router.post("/create-checkout-session")
async def create_checkout_session(request: CheckoutSessionRequest):
    try:
        # First, attempt to map the plan_id to a stripe_price_id
        # Assuming we added stripe_price_id to our public.plans in Supabase
        if supabase:
            plan_res = supabase.table("plans").select("stripe_price_id, name").eq("id", request.plan_id).single().execute()
            if not plan_res.data or not plan_res.data.get("stripe_price_id"):
                raise HTTPException(status_code=400, detail="Plan does not have a valid Stripe Price configured")
            
            price_id = plan_res.data["stripe_price_id"]
        else:
            # Fallback if Supabase not configured
            # For testing with placeholder, use a mock or hardcoded logic
            price_id = "price_mock_premium" if "premium" in request.plan_id.lower() else "price_mock_plus"

        frontend_url = "http://localhost:8080" # Default local URL of pact-talk-ai

        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=frontend_url + '/subscriptions?success=true&session_id={CHECKOUT_SESSION_ID}',
            cancel_url=frontend_url + '/subscriptions?canceled=true',
            customer_email=request.email,
            client_reference_id=request.user_id,
        )

        return {"url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    
    event = None

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, webhook_secret
            )
        else:
            # If no webhook secret is configured (e.g., local dev without CLI), parse normally
            import json
            data = json.loads(payload)
            event = stripe.Event.construct_from(data, stripe.api_key)
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        user_id = session.get('client_reference_id')
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        
        if user_id and supabase:
            # When checkout is completed, we update the user's stripe info
            supabase.table("profiles").update({
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "subscription_status": "active"
                # To fully link, we'd also set the plan_id based on the price ID
            }).eq("user_id", user_id).execute()

    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        status = subscription.get('status')
        
        if supabase:
            supabase.table("profiles").update({
                "subscription_status": status
            }).eq("stripe_customer_id", customer_id).execute()

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        
        if supabase:
            # If subscription is canceled
            supabase.table("profiles").update({
                "subscription_status": "canceled",
                "plan_id": None # Reset plan_id if appropriate
            }).eq("stripe_customer_id", customer_id).execute()

    return {"status": "success"}

