"""Stripe payment integration for premium subscriptions."""

import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Payment, User
from app.routers.auth import get_current_user
from app.schemas import CheckoutSessionResponse, PaymentRecord, PaymentStatusResponse

router = APIRouter(prefix="/api/payments", tags=["payments"])
settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout session for premium upgrade.

    Requires authentication. Returns a checkout URL to redirect the user to.
    """
    # Authenticate user
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = authorization.replace("Bearer ", "")
    current_user = get_current_user(db, token)

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Check if user is already premium
    if current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already premium",
        )

    # CRITICAL: Check if user has a successful payment that wasn't processed yet
    # This prevents duplicate charges if:
    # - Service was down when payment succeeded
    # - User tries again after idempotency key expired (>24h)
    # - Webhook failed but payment succeeded

    # First check database
    existing_payment = (
        db.query(Payment)
        .filter(
            Payment.user_id == current_user.id,
            Payment.status == "succeeded",
        )
        .first()
    )

    # Also check Stripe directly (in case payment succeeded but wasn't recorded)
    try:
        sessions = stripe.checkout.Session.list(
            customer_details={"email": current_user.email},
            limit=5,
        )

        for session in sessions.data:
            if (
                session.status == "complete"
                and session.payment_status == "paid"
                and session.metadata.get("user_id") == str(current_user.id)
            ):
                # Found successful payment on Stripe
                if not current_user.is_premium:
                    current_user.is_premium = True
                    db.commit()
                    logger.info(
                        f"Found successful payment on Stripe for user {current_user.id}, upgraded to premium"
                    )

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You already have a successful payment. Premium status has been updated.",
                )

    except stripe.error.StripeError as e:
        logger.warning(f"Could not check Stripe for existing payments: {e}")
        # Continue anyway - if Stripe is down, still allow creating checkout

    if existing_payment:
        # User already paid but isn't premium yet - upgrade them now
        if not current_user.is_premium:
            current_user.is_premium = True
            db.commit()
            logger.info(
                f"Found existing successful payment in DB for user {current_user.id}, upgraded to premium"
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a successful payment. Premium status has been updated.",
        )

    # Validate Stripe configuration
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe is not configured",
        )

    if not settings.STRIPE_PREMIUM_PRICE_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Premium price not configured",
        )

    try:
        # Use idempotency key to prevent duplicate charges
        # Format: user_{user_id}_premium - unique per user for premium upgrade
        # Stripe caches responses for 24 hours with the same key
        idempotency_key = f"user_{current_user.id}_premium_upgrade"

        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": settings.STRIPE_PREMIUM_PRICE_ID,
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
            customer_email=current_user.email,
            metadata={
                "user_id": current_user.id,
            },
            idempotency_key=idempotency_key,
        )

        logger.info(f"Created checkout session for user {current_user.id}: {checkout_session.id}")

        return CheckoutSessionResponse(checkout_url=checkout_session.url)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}",
        )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Stripe webhook events.

    This endpoint is called by Stripe when events occur (e.g., successful payment).
    Signature verification ensures the webhook is legitimate.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        # Invalid payload
        logger.error("Invalid webhook payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        logger.error("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_completed(session, db)
    else:
        logger.info(f"Unhandled webhook event type: {event['type']}")

    return {"status": "success"}


async def handle_checkout_completed(session: dict, db: Session):
    """
    Handle successful checkout completion.

    Marks user as premium and creates payment record.
    """
    user_id = session.get("metadata", {}).get("user_id")
    payment_intent_id = session.get("payment_intent")

    if not user_id:
        logger.error(f"Missing user_id in checkout session metadata: {session.get('id')}")
        return

    # Check if payment already processed (idempotency)
    existing_payment = (
        db.query(Payment).filter(Payment.stripe_payment_id == payment_intent_id).first()
    )

    if existing_payment:
        logger.info(f"Payment {payment_intent_id} already processed, skipping")
        return

    # Get user
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.error(f"User {user_id} not found for payment {payment_intent_id}")
        return

    try:
        # Create payment record
        payment = Payment(
            user_id=user_id,
            stripe_payment_id=payment_intent_id,
            amount_cents=500,  # $5.00
            status="succeeded",
        )
        db.add(payment)

        # Mark user as premium
        user.is_premium = True

        # Commit transaction
        db.commit()

        logger.info(f"Successfully processed payment for user {user_id}: {payment_intent_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing payment for user {user_id}: {e}")
        raise


@router.post("/verify-payment")
async def verify_payment(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    Verify payment completion after Stripe checkout redirect.

    This endpoint is called by the success page to verify the payment actually
    succeeded on Stripe's side and upgrade the user to premium if needed.

    This is the PRIMARY mechanism for granting premium status - webhooks are backup.
    """
    # Authenticate user
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = authorization.replace("Bearer ", "")
    current_user = get_current_user(db, token)

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # If already premium, nothing to do
    if current_user.is_premium:
        logger.info(f"User {current_user.id} already premium, skipping verification")
        return {"status": "already_premium", "is_premium": True}

    try:
        # Search Stripe for successful payments for this customer
        # We search by email since that's what we pass to Stripe
        sessions = stripe.checkout.Session.list(
            customer_details={"email": current_user.email},
            limit=10,
        )

        # Find a completed session with our user_id in metadata
        for session in sessions.data:
            if (
                session.status == "complete"
                and session.payment_status == "paid"
                and session.metadata.get("user_id") == str(current_user.id)
            ):
                # Found a successful payment! Process it
                payment_intent_id = session.payment_intent

                # Check if already processed (idempotency)
                existing_payment = (
                    db.query(Payment).filter(Payment.stripe_payment_id == payment_intent_id).first()
                )

                if not existing_payment:
                    # Create payment record
                    payment = Payment(
                        user_id=current_user.id,
                        stripe_payment_id=payment_intent_id,
                        amount_cents=session.amount_total,  # Use actual amount from Stripe
                        status="succeeded",
                    )
                    db.add(payment)

                    # Mark user as premium
                    current_user.is_premium = True
                    db.commit()

                    logger.info(
                        f"Successfully verified and processed payment for user {current_user.id}: {payment_intent_id}"
                    )
                    return {"status": "verified_and_upgraded", "is_premium": True}
                else:
                    # Payment already recorded, just upgrade user if needed
                    if not current_user.is_premium:
                        current_user.is_premium = True
                        db.commit()
                        logger.info(
                            f"Upgraded user {current_user.id} to premium (payment already recorded)"
                        )
                        return {"status": "upgraded", "is_premium": True}
                    else:
                        return {"status": "already_processed", "is_premium": True}

        # No successful payment found
        logger.warning(f"No successful payment found for user {current_user.id}")
        return {"status": "no_payment_found", "is_premium": False}

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error verifying payment for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify payment: {str(e)}",
        )


@router.post("/refund/{payment_intent_id}")
async def refund_payment(
    payment_intent_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    Refund a payment by payment_intent_id.

    Only admins or the payment owner can refund.
    Useful for refunding duplicate charges.
    """
    # Authenticate user
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = authorization.replace("Bearer ", "")
    current_user = get_current_user(db, token)

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Get payment record
    payment = db.query(Payment).filter(Payment.stripe_payment_id == payment_intent_id).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    # Check authorization (must be admin or payment owner)
    if not current_user.is_admin and payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to refund this payment",
        )

    # Check if already refunded
    if payment.status == "refunded":
        return {"status": "already_refunded", "payment_id": payment_intent_id}

    try:
        # Refund via Stripe
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            reason="duplicate",
        )

        # Update payment record
        payment.status = "refunded"
        db.commit()

        logger.info(f"Refunded payment {payment_intent_id} for user {payment.user_id}")

        return {
            "status": "refunded",
            "payment_id": payment_intent_id,
            "refund_id": refund.id,
            "amount_cents": payment.amount_cents,
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error refunding payment {payment_intent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refund payment: {str(e)}",
        )


@router.get("/status", response_model=PaymentStatusResponse)
def get_payment_status(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    Get current user's premium status and payment history.

    Requires authentication.
    """
    # Authenticate user
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = authorization.replace("Bearer ", "")
    current_user = get_current_user(db, token)

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Get user's payments
    payments = db.query(Payment).filter(Payment.user_id == current_user.id).all()

    return PaymentStatusResponse(
        is_premium=current_user.is_premium,
        payments=[
            PaymentRecord(
                id=p.id,
                stripe_payment_id=p.stripe_payment_id,
                amount_cents=p.amount_cents,
                status=p.status,
                created_at=p.created_at,
            )
            for p in payments
        ],
    )
