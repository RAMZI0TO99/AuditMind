# routers/payments.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import stripe
import os
import models
from dependencies import get_db, get_current_user

router = APIRouter(tags=["Payments"])
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

@router.post("/api/create-checkout-session")
async def create_checkout_session(current_user: models.User = Depends(get_current_user)):
    try:
        DOMAIN = os.environ.get("FRONTEND_URL", "https://miniature-tribble-97j474wjqwqvf9rxj-8000.app.github.dev")

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': 2900, 
                    'product_data': {
                        'name': 'Compliance Guard Pro',
                        'description': 'Unlock Multi-Tenant Knowledge Base and Custom Rules',
                    },
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            success_url=f"{DOMAIN}/?success=true",
            cancel_url=f"{DOMAIN}/?canceled=true",
            client_reference_id=str(current_user.id),
            customer_email=current_user.email
        )
        return {"url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/create-portal-session")
async def create_portal_session(current_user: models.User = Depends(get_current_user)):
    try:
        # 1. Ask Stripe to find the customer ID associated with this user's email
        customers = stripe.Customer.list(email=current_user.email, limit=1)
        
        if not customers.data:
            raise HTTPException(status_code=400, detail="No active Stripe customer found.")
            
        customer_id = customers.data[0].id
        DOMAIN = os.environ.get("FRONTEND_URL", "https://miniature-tribble-97j474wjqwqvf9rxj-8000.app.github.dev")

        # 2. Generate the secure portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=DOMAIN,
        )
        return {"url": portal_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET") 

    if not webhook_secret:
        raise HTTPException(status_code=400, detail="Missing secret")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Webhook error")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get("client_reference_id") 

        if user_id:
            user = db.query(models.User).filter(models.User.id == int(user_id)).first()
            if user:
                user.tier = "pro"
                db.commit()
                print(f"🎉 SUCCESS! User {user.email} upgraded to PRO tier!")

    return {"status": "success"}

@router.get("/api/dev/force-pro")
async def force_pro_upgrade(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.tier = "pro"
    db.commit()
    return {"message": f"Success! {current_user.email} is now a PRO user."}