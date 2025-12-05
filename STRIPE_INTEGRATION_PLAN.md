# Stripe Integration Implementation Plan

## Overview
Integrate Stripe payment processing to enable $5 one-time premium upgrade for unlimited Norwood analyses. The existing database schema already has the `payments` table and `is_premium` flag on users - we just need to wire up the Stripe checkout flow and webhook handler.

---

## Architecture Decisions

### Payment Flow: Stripe Checkout (Recommended)
**Why:** Stripe Checkout is hosted by Stripe, handles payment methods, 3D Secure, compliance, and gives you a complete payment UI without building forms.

**Flow:**
1. User clicks "Upgrade to Premium"
2. Backend creates Stripe Checkout Session → returns session URL
3. User redirected to Stripe-hosted payment page
4. After payment, Stripe redirects back to success URL
5. Stripe webhook fires `checkout.session.completed` → backend marks user as premium
6. User redirected to dashboard with premium features unlocked

**Alternative considered:** Stripe Payment Intents (requires building custom payment form - more work, not needed for simple one-time payment)

### Webhook Security
- Verify webhook signatures using Stripe's signing secret
- Use raw request body for signature validation (critical!)
- Idempotency: check if payment already processed before updating user

### Error Handling
- Webhook failures: return 500 → Stripe will retry automatically
- Payment failures: user sees error on Stripe page, no database changes
- Race conditions: use database transactions when marking user premium

---

## Implementation Steps

### 1. Add Stripe Dependency
**File:** `pyproject.toml`

Add `stripe>=8.0.0` to dependencies.

**Why:** Official Stripe Python SDK for creating checkout sessions and verifying webhooks.

---

### 2. Add Stripe Configuration
**File:** `app/config.py`

Add these settings to the `Settings` class:
```python
# Stripe
STRIPE_SECRET_KEY: str = ""
STRIPE_PUBLISHABLE_KEY: str = ""  # For frontend if needed
STRIPE_WEBHOOK_SECRET: str = ""
STRIPE_PREMIUM_PRICE_ID: str = ""  # Stripe Price ID for $5 product
STRIPE_SUCCESS_URL: str = "http://localhost:8000/checkout/success"
STRIPE_CANCEL_URL: str = "http://localhost:8000/checkout/cancel"
```

**Note:** User will need to create:
1. Stripe account
2. Create a Product in Stripe Dashboard
3. Create a Price ($5 one-time payment)
4. Copy Price ID to config
5. Get API keys from Stripe Dashboard
6. Set up webhook endpoint in Stripe Dashboard → get webhook secret

---

### 3. Create Payment Router
**File:** `app/routers/payments.py` (NEW FILE)

**Endpoints:**

**POST /api/payments/create-checkout-session**
- Requires authentication
- Check if user already premium → return error
- Create Stripe Checkout Session with:
  - Price ID from config
  - Customer email from user
  - Success/cancel URLs
  - Metadata: `user_id`
  - Mode: 'payment' (one-time)
- Return: `{ checkout_url: "https://checkout.stripe.com/..." }`

**POST /api/payments/webhook**
- NO authentication (Stripe calls this)
- Verify webhook signature using `STRIPE_WEBHOOK_SECRET`
- Handle event: `checkout.session.completed`
  - Extract `user_id` from session metadata
  - Extract `payment_intent` ID
  - Create Payment record in database (status: 'succeeded')
  - Mark user as `is_premium = True`
  - Commit transaction
- Return 200 on success, 400/500 on failure

**GET /api/payments/status** (Optional)
- Requires authentication
- Return user's premium status and payment history
- Useful for debugging

---

### 4. Add Payment Schemas
**File:** `app/schemas.py`

Add these Pydantic schemas:
```python
class CheckoutSessionResponse(BaseModel):
    checkout_url: str = Field(..., description="Stripe Checkout URL to redirect user to")

class PaymentStatusResponse(BaseModel):
    is_premium: bool
    payments: list[PaymentRecord]

class PaymentRecord(BaseModel):
    id: str
    stripe_payment_id: str
    amount_cents: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

---

### 5. Update Auth Router Response
**File:** `app/routers/auth.py`

The `UserResponse` schema already includes `is_premium` and `free_analyses_remaining`, so no changes needed there. Just verify the `/api/auth/me` endpoint returns these fields correctly.

---

### 6. Protect Analysis Endpoint (Optional for this phase)
**File:** `app/main.py` or create `app/routers/analyze.py`

Current `/analyze` endpoint doesn't check premium status. For now, we can leave it open OR add a simple check:

```python
@router.post("/analyze")
async def submit_analysis(
    file: UploadFile,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    # If user is authenticated and not premium, check free analyses
    if current_user and not current_user.is_premium:
        if current_user.free_analyses_remaining <= 0:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail="No free analyses remaining. Upgrade to premium for unlimited analyses.",
            )
        # Decrement counter
        current_user.free_analyses_remaining -= 1
        db.commit()

    # Continue with existing logic...
```

**Decision:** Should we enforce this now, or leave analysis open for testing? User preference?

---

### 7. Frontend Integration (Quick Overview)
**Not part of backend implementation, but user will need:**

1. Add "Upgrade to Premium" button that:
   - Calls `POST /api/payments/create-checkout-session` with auth token
   - Redirects to returned `checkout_url`

2. Success page at `/checkout/success`:
   - Shows "Payment successful! You're now premium"
   - Refetches user data to update UI

3. Cancel page at `/checkout/cancel`:
   - Shows "Payment canceled" message

---

## Testing Plan

### Local Testing (Stripe Test Mode)
1. Use Stripe test API keys (start with `sk_test_...`)
2. Use Stripe CLI for webhook forwarding:
   ```bash
   stripe listen --forward-to localhost:8000/api/payments/webhook
   ```
3. Test checkout with test card: `4242 4242 4242 4242`

### Test Cases
1. ✅ Create checkout session as authenticated user
2. ✅ Complete payment with test card → verify user marked premium
3. ✅ Webhook signature verification fails → returns 400
4. ✅ Duplicate webhook (same payment_intent) → idempotent (no error)
5. ✅ User already premium → can't create checkout session
6. ❌ Unauthenticated user tries to create checkout → 401 error

---

## Environment Variables Needed

Add to `.env`:
```bash
# Stripe
STRIPE_SECRET_KEY=sk_test_... (test) or sk_live_... (production)
STRIPE_PUBLISHABLE_KEY=pk_test_... (optional, for frontend)
STRIPE_WEBHOOK_SECRET=whsec_... (from Stripe Dashboard webhook setup)
STRIPE_PREMIUM_PRICE_ID=price_... (from Stripe Product/Price creation)
STRIPE_SUCCESS_URL=http://localhost:8000/checkout/success
STRIPE_CANCEL_URL=http://localhost:8000/checkout/cancel
```

---

## Files to Create/Modify

### New Files
- `app/routers/payments.py` - Stripe checkout and webhook handlers

### Modified Files
- `pyproject.toml` - Add stripe dependency
- `app/config.py` - Add Stripe settings
- `app/schemas.py` - Add payment response schemas
- `app/main.py` - Import and include payments router
- `.env` - Add Stripe configuration

### Optional Enhancements (Future)
- `app/main.py` - Add premium enforcement to `/analyze` endpoint
- Add proper error handling and logging
- Add payment history endpoint
- Add admin endpoint to manually grant premium

---

## Stripe Dashboard Setup Steps

1. Create Stripe account (test mode)
2. Products → Create Product:
   - Name: "Norwood AI Premium"
   - Description: "Unlimited hairline analyses and projections"
3. Add Price:
   - One-time payment
   - Amount: $5.00 USD
   - Copy Price ID (e.g., `price_1ABC...`)
4. Developers → API Keys:
   - Copy "Secret key" (starts with `sk_test_`)
   - Copy "Publishable key" (starts with `pk_test_`)
5. Developers → Webhooks → Add endpoint:
   - Endpoint URL: `https://yourdomain.com/api/payments/webhook`
   - Events to listen: `checkout.session.completed`
   - Copy "Signing secret" (starts with `whsec_`)

---

## Security Considerations

1. **Webhook Signature Verification**: CRITICAL - always verify webhook signatures to prevent fake payment notifications
2. **HTTPS Required**: Stripe webhooks require HTTPS in production (use ngrok or similar for local testing)
3. **Idempotency**: Check if payment already processed using `stripe_payment_id` unique constraint
4. **Raw Request Body**: Must use raw request body for signature verification (FastAPI caveat - need special handling)
5. **Metadata Security**: Never trust client-provided user_id - always use authenticated user from session

---

## Cost & Pricing

- Stripe Fee: 2.9% + $0.30 per transaction
- $5.00 payment → $4.55 net revenue
- No monthly fees for standard Stripe account
- First $1M in revenue: standard rates
- Webhook delivery: free, unlimited

---

## Migration Path

Since database schema already exists:
1. ✅ `users.is_premium` field exists
2. ✅ `payments` table exists with `stripe_payment_id` column
3. ✅ No migrations needed
4. Just need to implement the endpoints and webhook handler

---

## Questions for User

1. **Analysis enforcement**: Should we enforce premium checks on `/analyze` now, or later?
2. **Stripe account**: Do you already have a Stripe account, or need to create one?
3. **Testing approach**: Want to use Stripe test mode first, or go straight to production setup?
4. **Success/Cancel URLs**: Should these be separate frontend pages, or just show modals?

---

## Estimated Implementation Time

- Add dependency and config: 5 minutes
- Create payment router with checkout session: 20 minutes
- Implement webhook handler: 30 minutes
- Add schemas and tests: 15 minutes
- **Total backend work: ~70 minutes**

Frontend integration (separate):
- Add checkout button: 10 minutes
- Success/cancel pages: 15 minutes
- **Total frontend work: ~25 minutes**

---

## Next Steps

1. User approves this plan
2. Install Stripe dependency
3. Add Stripe config to settings
4. Create payment router with endpoints
5. Add payment schemas
6. Register router in main.py
7. Test locally with Stripe CLI
8. Update frontend to integrate checkout button
