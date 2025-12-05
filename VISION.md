# Norwood AI - Product Vision

A brutally honest AI-powered baldness analysis service. Upload a photo, get roasted about your hairline, and watch your follicular future unfold.

## Core Flow

1. **Landing Page** → User hits the site, sees the pitch
2. **Google OAuth** → Login with Google (no passwords to manage)
3. **Free Analysis** → Every user gets 1 free Norwood analysis
4. **Paywall** → Want more? $5 one-time payment unlocks everything
5. **Premium Features** → Unlimited analyses + future projections

---

## Features

### Free Tier
- 1 Norwood analysis
- Stage classification (1-7)
- Confidence level
- The Roast™

### Premium ($5 one-time)
- Unlimited Norwood analyses
- Full analysis history
- **Norwood Projections** - AI-generated images showing your hairline at:
  - 1 year out
  - 3 years out
  - 5 years out
  - 15 years out
- Progression tracking over time

---

## User Experience

### Sidebar (authenticated users)
```
┌─────────────────────┐
│  NORWOOD AI         │
├─────────────────────┤
│  + New Analysis     │
├─────────────────────┤
│  History            │
│  ├─ Dec 4, 2024     │
│  ├─ Nov 15, 2024    │
│  └─ Oct 2, 2024     │
├─────────────────────┤
│  Projections        │ ← Premium only
├─────────────────────┤
│  Account            │
│  └─ Upgrade to Pro  │ ← If free tier
└─────────────────────┘
```

### Analysis Result Page
- Original uploaded image
- Norwood stage (big, prominent)
- Confidence meter
- THE VERDICT (roast)
- Technical reasoning (collapsible)
- [Generate Projections] button (premium)

### Projections Page (Premium)
- Side-by-side or carousel view
- Current photo + 1yr / 3yr / 5yr / 15yr projections
- Download all as ZIP
- Share individual projections (optional)

---

## Database Schema

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | ULID | Primary key (sortable, URL-friendly) |
| google_id | VARCHAR | From OAuth |
| email | VARCHAR | Unique |
| name | VARCHAR | Display name |
| avatar_url | VARCHAR | Google profile pic |
| is_premium | BOOLEAN | Default false |
| free_analyses_remaining | INTEGER | Default 1 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### `payments`
| Column | Type | Notes |
|--------|------|-------|
| id | ULID | Primary key |
| user_id | ULID | FK → users |
| stripe_payment_id | VARCHAR | Stripe reference |
| amount_cents | INTEGER | 500 ($5.00) |
| status | VARCHAR | succeeded, failed, pending |
| created_at | TIMESTAMP | |

### `analyses`
| Column | Type | Notes |
|--------|------|-------|
| id | ULID | Primary key |
| user_id | ULID | FK → users |
| image_url | VARCHAR | S3 path to uploaded image |
| norwood_stage | INTEGER | 1-7 |
| confidence | VARCHAR | high, medium, low |
| roast | TEXT | The brutal truth |
| reasoning | TEXT | Technical explanation |
| created_at | TIMESTAMP | |

### `projections`
| Column | Type | Notes |
|--------|------|-------|
| id | ULID | Primary key |
| analysis_id | ULID | FK → analyses |
| user_id | ULID | FK → users |
| years_out | INTEGER | 1, 3, 5, or 15 |
| image_url | VARCHAR | S3 path to generated image |
| created_at | TIMESTAMP | |

---

## Technical Scaffolding

### Backend Additions

```
app/
├── main.py              # Add auth routes, user routes
├── config.py            # Add Google OAuth, Stripe, S3 config
├── models/              # NEW - SQLAlchemy models
│   ├── __init__.py
│   ├── user.py
│   ├── payment.py
│   ├── analysis.py
│   └── projection.py
├── routers/             # NEW - Split routes into modules
│   ├── __init__.py
│   ├── auth.py          # Google OAuth endpoints
│   ├── analyze.py       # Analysis endpoints
│   ├── projections.py   # Projection generation
│   ├── payments.py      # Stripe webhooks
│   └── users.py         # User profile, history
├── services/            # NEW - Business logic
│   ├── __init__.py
│   ├── auth.py          # OAuth handling
│   ├── storage.py       # S3 upload/download
│   ├── payments.py      # Stripe integration
│   └── projections.py   # Image generation API calls
├── tasks/
│   ├── analyze.py       # Existing
│   └── generate_projection.py  # NEW - async projection generation
└── db.py                # NEW - Database connection
```

### Infrastructure Needed

| Service | Purpose | Provider |
|---------|---------|----------|
| PostgreSQL | User data, analyses, payments | AWS RDS or Supabase |
| Redis | Celery broker (existing) | Already have |
| S3 | Image storage (uploads + projections) | AWS S3 |
| Stripe | Payments | Stripe |
| Google OAuth | Authentication | Google Cloud Console |
| Image Generation | Projections | Replicate / Stability AI / DALL-E |

### Frontend Additions

```
frontend/src/
├── App.vue              # Add router, auth state
├── router/              # NEW
│   └── index.js
├── stores/              # NEW - Pinia state management
│   ├── auth.js
│   └── user.js
├── views/               # NEW - Page components
│   ├── Landing.vue
│   ├── Dashboard.vue
│   ├── Analysis.vue
│   ├── Projections.vue
│   ├── History.vue
│   └── Account.vue
├── components/          # NEW - Reusable components
│   ├── Sidebar.vue
│   ├── AnalysisCard.vue
│   ├── ProjectionGallery.vue
│   ├── PaywallModal.vue
│   └── GoogleLoginButton.vue
└── services/            # NEW - API calls
    └── api.js
```

---

## Implementation Phases

### Phase 1: Auth & Database
- [ ] Set up PostgreSQL (RDS or Supabase)
- [ ] Create SQLAlchemy models
- [ ] Google OAuth integration
- [ ] JWT session management
- [ ] Protected routes

### Phase 2: User Experience
- [ ] Vue Router setup
- [ ] Sidebar + Dashboard layout
- [ ] Analysis history page
- [ ] Store analyses in DB (not just return them)

### Phase 3: Payments
- [ ] Stripe integration
- [ ] Checkout flow
- [ ] Webhook handler for payment confirmation
- [ ] Premium flag on user

### Phase 4: Image Storage
- [ ] S3 bucket setup
- [ ] Upload images to S3 instead of base64
- [ ] Serve images via signed URLs or CloudFront

### Phase 5: Projections
- [ ] Pick image generation API (Replicate likely best)
- [ ] Projection generation task
- [ ] Projections UI
- [ ] Store generated images in S3

### Phase 6: Polish
- [ ] Landing page design
- [ ] Email notifications (optional)
- [ ] Rate limiting
- [ ] Error handling + logging
- [ ] Mobile responsive

---

## Cost Estimates

| Service | Cost |
|---------|------|
| EC2 (t3.small) | ~$15/mo |
| RDS (db.t3.micro) | ~$15/mo |
| S3 | ~$1/mo (minimal at first) |
| Replicate (projections) | ~$0.01-0.05 per image |
| Domain | ~$12/yr |
| **Total** | **~$30-40/mo** + per-projection costs |

Break-even: ~6-8 premium users/month

---

## Backend Standards (from Marmot)

### Pydantic Schemas
- **Separate schemas per operation**: `UserCreate`, `UserUpdate`, `UserResponse`
- **No raw dicts** - every route returns a typed Pydantic model
- **Field descriptions** for OpenAPI docs: `Field(..., description="User's email")`
- **Validators** for complex logic:
```python
@field_validator("email", mode="before")
@classmethod
def normalize_email(cls, v):
    return v.lower().strip()

@model_validator(mode="after")
def check_premium_requirements(self):
    # cross-field validation
    return self
```

### Route Organization
```
app/routers/
├── auth.py          # Google OAuth, JWT
├── analyze.py       # POST /analyze, GET /analyses/{id}
├── users.py         # GET /me, PATCH /me
├── payments.py      # POST /checkout, webhooks
└── projections.py   # POST /projections, GET /projections/{id}
```

Each router:
```python
router = APIRouter(prefix="/analyses", tags=["analyses"])

@router.post("/", response_model=AnalysisResponse, status_code=201)
def create_analysis(
    request: AnalysisCreate,
    current_user: User = Depends(get_current_user),
    analysis_service: AnalysisService = Depends(get_analysis_service),
):
    return analysis_service.create(current_user, request)
```

### Service Layer Pattern
**Thin routes, rich services.** Routes handle HTTP concerns, services handle business logic.

```python
# services/analysis_service.py
class AnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user: User, request: AnalysisCreate) -> Analysis:
        if not user.is_premium and user.free_analyses_remaining <= 0:
            raise PaywallError("No free analyses remaining")

        # business logic here
        analysis = Analysis(user_id=user.id, ...)
        self.db.add(analysis)
        self.db.commit()
        return analysis
```

### Custom Exception Hierarchy
```python
# exceptions.py
class NorwoodError(Exception):
    """Base exception"""

class PaywallError(NorwoodError):
    """User needs to pay"""

class AnalysisNotFoundError(NorwoodError):
    """Analysis doesn't exist"""

# In routes - map to HTTP
except PaywallError:
    raise HTTPException(status_code=402, detail="Payment required")
except AnalysisNotFoundError:
    raise HTTPException(status_code=404, detail="Analysis not found")
```

### Database Models
```python
# models/base.py
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# models/user.py
from ulid import ULID

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    google_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    is_premium = Column(Boolean, default=False)

    analyses = relationship("Analysis", back_populates="user")
```

### Migrations
Raw SQL migrations in `migrations/` folder, applied in order:
```
migrations/
├── 001_create_users.sql
├── 002_create_payments.sql
├── 003_create_analyses.sql
├── 004_create_projections.sql
└── ...
```

Each migration file:
```sql
-- migrations/001_create_users.sql
CREATE TABLE IF NOT EXISTS users (
    id CHAR(26) PRIMARY KEY,  -- ULID generated in app
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar_url TEXT,
    is_premium BOOLEAN DEFAULT FALSE,
    free_analyses_remaining INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_email ON users(email);
```

Simple migration runner in Makefile:
```bash
make migrate  # runs all .sql files in order
```

### Dependency Injection
```python
# dependencies.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    # validate JWT, fetch user
    return user

def get_analysis_service(db: Session = Depends(get_db)) -> AnalysisService:
    return AnalysisService(db)
```

### Response Models (no raw dicts ever)
```python
# schemas/analysis.py
class AnalysisCreate(BaseModel):
    image_base64: str

class AnalysisResponse(BaseModel):
    id: str  # ULID
    norwood_stage: int
    confidence: str
    roast: str
    reasoning: str
    image_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## Open Questions

1. **Image generation model** - Which API for projections? Replicate has good options
2. **Projection accuracy** - How to make them look realistic vs comedic?
3. **Sharing** - Let users share their roasts publicly?
4. **Referrals** - Give free analyses for referring friends?
5. **Mobile app** - Eventually? Or PWA good enough?
