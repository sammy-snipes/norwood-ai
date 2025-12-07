# Backend Development Guide

## Project Structure

```
app/
├── main.py                 # FastAPI app, core routes, task polling
├── config.py               # Settings with AWS Secrets Manager
├── db.py                   # Database engine & session management
├── celery_worker.py        # Celery configuration
├── schemas.py              # Pydantic response models
├── models/                 # SQLAlchemy ORM models
├── routers/                # FastAPI route handlers
├── tasks/                  # Celery async tasks
├── services/               # Business logic (S3, PDF, secrets)
└── llm/                    # Anthropic Claude integration
```

## Key Patterns

### 1. Authentication

All auth uses Google OAuth + JWT Bearer tokens.

```python
# Extract and validate token in any endpoint:
from app.routers.auth import decode_token

@router.post("/my-endpoint")
def my_endpoint(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = db.query(User).filter(User.id == user_id).first()
```

For premium-only endpoints, check `user.is_premium or user.is_admin`:

```python
if not user.is_premium and not user.is_admin:
    raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED)
```

### 2. JSONB Updates (CRITICAL)

SQLAlchemy doesn't detect mutations inside JSONB dicts. Always use `flag_modified`:

```python
from sqlalchemy.orm.attributes import flag_modified

# Update JSONB field
options = user.options or {}
options["my_flag"] = True
user.options = options
flag_modified(user, "options")  # REQUIRED
db.commit()
```

### 3. Database Sessions

**In FastAPI routes** - use dependency injection:

```python
@router.get("/endpoint")
def my_route(db: Session = Depends(get_db)):
    return db.query(User).all()
    # Session auto-closes after request
```

**In Celery tasks** - use context manager:

```python
from app.db import get_db_context

@celery_app.task(bind=True)
def my_task(self):
    with get_db_context() as db:
        obj = db.query(Model).filter(...).first()
        obj.status = "completed"
        # Auto-commits on exit, auto-rollbacks on exception
```

### 4. Celery Tasks

Tasks return dicts with success flag. Client polls `/tasks/{task_id}`.

```python
# app/tasks/my_feature.py
from app.celery_worker import celery_app
from app.db import get_db_context

@celery_app.task(bind=True, name="my_task")
def my_task(self, param1: str, user_id: str) -> dict:
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting task for user {user_id}")

    try:
        with get_db_context() as db:
            # Do work
            result = process_something(param1)

            # Update DB
            obj = db.query(MyModel).filter(...).first()
            obj.result = result

        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"[{task_id}] Task failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

Queue from endpoint:

```python
@router.post("/trigger", response_model=TaskResponse, status_code=202)
def trigger_task(request: MyRequest, user: User, db: Session):
    task = my_task.delay(request.param1, user.id)
    return TaskResponse(task_id=task.id, status="pending")
```

### 5. Models

All models use ULID IDs and timestamps:

```python
from sqlalchemy import Column, DateTime, String, func
from ulid import ULID
from app.models.base import Base

class MyModel(Base):
    __tablename__ = "my_models"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="my_models")
```

Add relationship to User model:

```python
# app/models/user.py
my_models = relationship("MyModel", back_populates="user", cascade="all, delete-orphan")
```

### 6. Schemas

Response schemas use `from_attributes` for ORM mapping:

```python
# app/schemas.py
class MyModelResponse(BaseModel):
    id: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

### 7. Routers

Register in `main.py`:

```python
from app.routers.my_feature import router as my_feature_router
app.include_router(my_feature_router)
```

## Adding a New Feature

1. **Model** (`app/models/my_feature.py`)
   - ULID primary key
   - Foreign key to users with CASCADE
   - Add relationship to User model
   - Export in `app/models/__init__.py`

2. **Schema** (`app/schemas.py`)
   - Request model if needed
   - Response model with `from_attributes = True`

3. **Router** (`app/routers/my_feature.py`)
   - Prefix: `/api/my-feature`
   - Auth check at start of each endpoint
   - Premium check if needed (402 if not premium)

4. **Task** (`app/tasks/my_feature.py`) if async work needed
   - Use `get_db_context()` for DB access
   - Return dict with `success` key
   - Log with `[{task_id}]` prefix

5. **Migration** (`migrations/YYYY_MM_DD_N_description.sql`)

## Code Style

- Type hints on all functions
- Imports: stdlib, third-party, then app imports
- Brief docstrings (one line unless complex)
- Log with task_id in Celery tasks
- Use `status.HTTP_*` constants for status codes

## Common Status Codes

- 200: Success
- 201: Created
- 202: Accepted (task queued)
- 400: Bad request
- 401: Unauthorized (not logged in)
- 402: Payment required (not premium)
- 404: Not found
- 500: Server error
