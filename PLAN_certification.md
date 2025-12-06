# Norwood Certification Feature + LLM Refactor

## Overview

Add a premium "Norwood Certification" feature that requires 3 validated photos (front, left, right), produces a clinical diagnosis, and generates a university-style PDF certificate. Simultaneously refactor all LLM calls to use a clean Pydantic-based abstraction.

---

## Phase 1: LLM Infrastructure

### New Files

**`app/llm/__init__.py`**
```python
from app.llm.executor import execute_vision_task, execute_text_task
from app.llm.client import get_client

__all__ = ["execute_vision_task", "execute_text_task", "get_client"]
```

**`app/llm/client.py`**
```python
"""Anthropic client singleton."""
import anthropic
from functools import lru_cache
from app.config import settings

@lru_cache
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
```

**`app/llm/executor.py`**
```python
"""
Core LLM execution functions with Pydantic structured output.
Uses tool forcing for guaranteed schema compliance.
"""
from typing import TypeVar
from pydantic import BaseModel
import json
import logging

from app.llm.client import get_client

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "claude-sonnet-4-20250514"


def execute_vision_task(
    images: list[tuple[str, str]],  # [(base64_data, media_type), ...]
    system_prompt: str,
    response_model: type[T],
    user_text: str = "Analyze the provided image(s).",
    model: str = DEFAULT_MODEL,
) -> T:
    """
    Send images to Claude, return validated Pydantic model.

    Uses tool forcing to guarantee structured output matching response_model schema.
    """
    client = get_client()

    # Build content blocks
    content = []
    for base64_data, media_type in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64_data,
            }
        })
    content.append({"type": "text", "text": user_text})

    # Define tool from Pydantic schema
    tool_name = response_model.__name__
    tool = {
        "name": tool_name,
        "description": f"Return the {tool_name} result",
        "input_schema": response_model.model_json_schema(),
    }

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": content}],
    )

    # Extract tool use block
    tool_use = next(
        (block for block in response.content if block.type == "tool_use"),
        None
    )

    if not tool_use:
        raise ValueError("No tool use in response")

    return response_model.model_validate(tool_use.input)


def execute_text_task(
    messages: list[dict],  # [{"role": "user"|"assistant", "content": str}, ...]
    system_prompt: str,
    response_model: type[T],
    model: str = DEFAULT_MODEL,
) -> T:
    """
    Send text conversation, return validated Pydantic model.
    """
    client = get_client()

    tool_name = response_model.__name__
    tool = {
        "name": tool_name,
        "description": f"Return the {tool_name} result",
        "input_schema": response_model.model_json_schema(),
    }

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        messages=messages,
    )

    tool_use = next(
        (block for block in response.content if block.type == "tool_use"),
        None
    )

    if not tool_use:
        raise ValueError("No tool use in response")

    return response_model.model_validate(tool_use.input)


def execute_text_task_plain(
    messages: list[dict],
    system_prompt: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Send text conversation, return plain text response.
    For cases where structured output isn't needed (e.g., counseling chat).
    """
    client = get_client()

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
    )

    text_block = next(
        (block for block in response.content if block.type == "text"),
        None
    )

    if not text_block:
        raise ValueError("No text in response")

    return text_block.text
```

### Schema Files

**`app/llm/schemas/__init__.py`**
```python
from app.llm.schemas.analysis import NorwoodAnalysisResult
from app.llm.schemas.counseling import CounselingResponse
from app.llm.schemas.certification import (
    PhotoValidationResult,
    CertificationDiagnosis,
)

__all__ = [
    "NorwoodAnalysisResult",
    "CounselingResponse",
    "PhotoValidationResult",
    "CertificationDiagnosis",
]
```

**`app/llm/schemas/base.py`**
```python
from pydantic import BaseModel, ConfigDict

class LLMSchema(BaseModel):
    """Base class for all LLM response schemas."""
    model_config = ConfigDict(extra="forbid")
```

**`app/llm/schemas/analysis.py`**
```python
"""Schema for Norwood analysis (existing feature)."""
from pydantic import Field
from app.llm.schemas.base import LLMSchema


class NorwoodAnalysisResult(LLMSchema):
    """Result from analyzing a single photo for Norwood stage."""

    norwood_stage: int = Field(
        ge=1, le=7,
        description="Norwood stage from 1-7"
    )
    confidence: str = Field(
        description="Confidence level: high, medium, or low"
    )
    title: str = Field(
        max_length=100,
        description="Punchy, memorable title for the analysis"
    )
    analysis_text: str = Field(
        description="Philosophical reflection on the diagnosis, stoic tone"
    )
    reasoning: str = Field(
        description="Clinical observations that led to this diagnosis"
    )
```

**`app/llm/schemas/counseling.py`**
```python
"""Schema for counseling responses (existing feature)."""
from app.llm.schemas.base import LLMSchema


class CounselingResponse(LLMSchema):
    """Response from the counseling AI."""

    content: str
```

**`app/llm/schemas/certification.py`**
```python
"""Schemas for Norwood Certification feature."""
from pydantic import Field
from app.llm.schemas.base import LLMSchema


class PhotoValidationResult(LLMSchema):
    """Result from validating a certification photo."""

    approved: bool = Field(
        description="Whether the photo meets quality requirements"
    )
    rejection_reason: str | None = Field(
        default=None,
        description="If rejected, why. E.g., 'Hairline obscured by hat'"
    )
    quality_notes: str = Field(
        description="What was observed about photo quality and hairline visibility"
    )


class CertificationDiagnosis(LLMSchema):
    """Clinical Norwood diagnosis from 3 validated photos."""

    norwood_stage: int = Field(
        ge=1, le=7,
        description="Norwood-Hamilton stage from 1-7"
    )
    norwood_variant: str | None = Field(
        default=None,
        description="Variant if applicable: 'A' (anterior) or 'V' (vertex)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score from 0.0 to 1.0"
    )
    clinical_assessment: str = Field(
        description="Formal clinical assessment in medical language"
    )
    observable_features: list[str] = Field(
        description="List of observed features supporting the diagnosis"
    )
    differential_considerations: str = Field(
        description="Why this stage vs adjacent stages, ruling out alternatives"
    )
```

---

## Phase 2: Refactor Existing Features

### Refactor `app/tasks/analyze.py`

Move prompt to separate constant, use executor:

```python
"""Norwood analysis task."""
import logging
from celery import shared_task

from app.llm import execute_vision_task
from app.llm.schemas import NorwoodAnalysisResult
from app.services.s3 import s3_service
from app.db import SessionLocal
from app.models.analysis import Analysis

logger = logging.getLogger(__name__)

NORWOOD_ANALYSIS_PROMPT = """You are a Norwood scale analyst with the gravitas of Marcus Aurelius
and the precision of a dermatologist. Analyze the provided image and determine the Norwood stage.

Guidelines:
- Stage 1: No significant hair loss or recession
- Stage 2: Slight recession at temples (mature hairline)
- Stage 3: Deeper temple recession, may form M-shape
- Stage 3V: Stage 3 with vertex (crown) thinning
- Stage 4: Further frontal loss and vertex thinning, band of hair separates the two
- Stage 5: Band between frontal and vertex narrows
- Stage 6: Frontal and vertex regions merge, band is gone
- Stage 7: Most severe, only horseshoe pattern remains

Provide your analysis with stoic wisdom. The title should be punchy and memorable.
The analysis_text should be a philosophical reflection on acceptance and the human condition."""


@shared_task(bind=True, max_retries=3)
def analyze_image(self, analysis_id: str, image_base64: str, content_type: str):
    """Analyze an image for Norwood stage."""
    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return {"success": False, "error": "Analysis not found"}

        # Execute LLM task
        result = execute_vision_task(
            images=[(image_base64, content_type)],
            system_prompt=NORWOOD_ANALYSIS_PROMPT,
            response_model=NorwoodAnalysisResult,
        )

        # Upload to S3
        s3_key = s3_service.upload_base64_image(
            image_base64, analysis.user_id, content_type
        )

        # Update analysis record
        analysis.norwood_stage = result.norwood_stage
        analysis.confidence = result.confidence
        analysis.title = result.title
        analysis.analysis_text = result.analysis_text
        analysis.reasoning = result.reasoning
        analysis.image_url = s3_key
        db.commit()

        return {
            "success": True,
            "norwood_stage": result.norwood_stage,
            "confidence": result.confidence,
            "title": result.title,
            "analysis_text": result.analysis_text,
            "reasoning": result.reasoning,
        }

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        db.close()
```

### Refactor `app/tasks/counseling.py`

Use `execute_text_task_plain` (counseling returns free-form text, not structured):

```python
"""Counseling response task."""
import logging
from celery import shared_task

from app.llm import execute_text_task_plain
from app.db import SessionLocal
from app.models.counseling import CounselingMessage, CounselingSession, MessageStatus
from app.models.analysis import Analysis

logger = logging.getLogger(__name__)


def build_counseling_prompt(user_analyses: list[Analysis]) -> str:
    """Build system prompt with user's analysis history."""

    history_section = ""
    if user_analyses:
        stages = [f"Stage {a.norwood_stage}" for a in user_analyses[:5]]
        history_section = f"\n\nUser's recent Norwood analyses: {', '.join(stages)}"

    return f"""You are a supportive hair loss counselor with warmth and dry humor.
You help users accept and cope with hair loss using stoic philosophy.

Guidelines:
- Be warm, empathetic, and occasionally use dry humor
- Reference stoic philosophy (Marcus Aurelius, Seneca, Epictetus)
- Focus on acceptance, not fighting nature
- NEVER recommend medical treatments (finasteride, minoxidil, transplants)
- If asked about treatments, redirect to acceptance and self-worth
- Keep responses conversational, 2-4 paragraphs max
- Use markdown formatting where appropriate
{history_section}"""


@shared_task(bind=True, max_retries=3)
def generate_counseling_response(self, message_id: str):
    """Generate AI response for a counseling message."""
    db = SessionLocal()
    try:
        message = db.query(CounselingMessage).filter(
            CounselingMessage.id == message_id
        ).first()

        if not message:
            return {"success": False, "error": "Message not found"}

        message.status = MessageStatus.processing
        db.commit()

        # Get session and conversation history
        session = db.query(CounselingSession).filter(
            CounselingSession.id == message.session_id
        ).first()

        messages_query = db.query(CounselingMessage).filter(
            CounselingMessage.session_id == session.id,
            CounselingMessage.status == MessageStatus.completed,
            CounselingMessage.id != message_id,
        ).order_by(CounselingMessage.created_at)

        # Build conversation history
        conversation = []
        for msg in messages_query:
            conversation.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        # Add the current user message that triggered this response
        user_msg = db.query(CounselingMessage).filter(
            CounselingMessage.session_id == session.id,
            CounselingMessage.role == "user",
            CounselingMessage.created_at < message.created_at,
        ).order_by(CounselingMessage.created_at.desc()).first()

        if user_msg:
            conversation.append({
                "role": "user",
                "content": user_msg.content,
            })

        # Get user's analysis history for context
        user_analyses = db.query(Analysis).filter(
            Analysis.user_id == session.user_id
        ).order_by(Analysis.created_at.desc()).limit(10).all()

        # Generate response
        response_text = execute_text_task_plain(
            messages=conversation,
            system_prompt=build_counseling_prompt(user_analyses),
        )

        message.content = response_text
        message.status = MessageStatus.completed
        db.commit()

        return {"success": True, "content": response_text}

    except Exception as e:
        logger.error(f"Counseling response failed: {e}", exc_info=True)
        if message:
            message.status = MessageStatus.failed
            db.commit()
        return {"success": False, "error": str(e)}
    finally:
        db.close()
```

---

## Phase 3: Certification Feature

### Database Migration

**`migrations/005_certification.sql`**
```sql
-- Certification photos
CREATE TABLE certification_photos (
    id VARCHAR(26) PRIMARY KEY,
    certification_id VARCHAR(26) NOT NULL REFERENCES certifications(id) ON DELETE CASCADE,
    photo_type VARCHAR(10) NOT NULL CHECK (photo_type IN ('front', 'left', 'right')),
    s3_key TEXT NOT NULL,
    validation_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending', 'approved', 'rejected')),
    rejection_reason TEXT,
    quality_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (certification_id, photo_type)
);

-- Certifications
CREATE TABLE certifications (
    id VARCHAR(26) PRIMARY KEY,
    user_id VARCHAR(26) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'photos_pending'
        CHECK (status IN ('photos_pending', 'analyzing', 'completed', 'failed')),
    norwood_stage INTEGER CHECK (norwood_stage >= 1 AND norwood_stage <= 7),
    norwood_variant VARCHAR(5),
    confidence FLOAT,
    clinical_assessment TEXT,
    observable_features JSONB,
    differential_considerations TEXT,
    pdf_s3_key TEXT,
    certified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_certifications_user_id ON certifications(user_id);
CREATE INDEX idx_certifications_created_at ON certifications(created_at);
CREATE INDEX idx_certification_photos_certification_id ON certification_photos(certification_id);
```

### Models

**`app/models/certification.py`**
```python
"""Certification models."""
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ulid import ULID
import enum

from app.models.base import Base, TimestampMixin


class PhotoType(str, enum.Enum):
    front = "front"
    left = "left"
    right = "right"


class ValidationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class CertificationStatus(str, enum.Enum):
    photos_pending = "photos_pending"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class CertificationPhoto(Base):
    __tablename__ = "certification_photos"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    certification_id = Column(
        String(26),
        ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    photo_type = Column(SAEnum(PhotoType), nullable=False)
    s3_key = Column(Text, nullable=False)
    validation_status = Column(
        SAEnum(ValidationStatus),
        nullable=False,
        default=ValidationStatus.pending
    )
    rejection_reason = Column(Text, nullable=True)
    quality_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    certification = relationship("Certification", back_populates="photos")


class Certification(Base, TimestampMixin):
    __tablename__ = "certifications"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status = Column(
        SAEnum(CertificationStatus),
        nullable=False,
        default=CertificationStatus.photos_pending
    )
    norwood_stage = Column(Integer, nullable=True)
    norwood_variant = Column(String(5), nullable=True)
    confidence = Column(Float, nullable=True)
    clinical_assessment = Column(Text, nullable=True)
    observable_features = Column(JSONB, nullable=True)
    differential_considerations = Column(Text, nullable=True)
    pdf_s3_key = Column(Text, nullable=True)
    certified_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="certifications")
    photos = relationship(
        "CertificationPhoto",
        back_populates="certification",
        cascade="all, delete-orphan",
        order_by="CertificationPhoto.created_at"
    )
```

**Update `app/models/user.py`** - Add relationship:
```python
certifications = relationship(
    "Certification",
    back_populates="user",
    cascade="all, delete-orphan"
)
```

### Prompts

**`app/llm/prompts/certification.py`**
```python
"""Prompts for certification feature."""

PHOTO_VALIDATION_PROMPT = """You are a quality control specialist for Norwood scale certification photos.

Your job is to determine if a photo is suitable for clinical hair loss assessment.

REQUIREMENTS FOR APPROVAL:
1. Hairline must be fully visible (pulled back, no hats/headbands obscuring it)
2. Adequate lighting (can clearly see hair density and scalp)
3. Correct angle for the photo type:
   - FRONT: Face-on view showing entire frontal hairline and temples
   - LEFT: Left side profile showing temple and side of head
   - RIGHT: Right side profile showing temple and side of head
4. In focus, not blurry
5. Hair not wet (wet hair obscures true density)

REJECT if:
- Hairline is partially or fully obscured (hat, hair covering forehead, headband)
- Too dark or overexposed to assess properly
- Wrong angle for the specified photo type
- Blurry or out of focus
- Only partial head visible

Be strict. This is for official certification. If in doubt, reject with clear reason."""


CERTIFICATION_DIAGNOSIS_PROMPT = """You are a clinical trichologist providing an official Norwood-Hamilton scale certification.

You have been provided three photos of the same individual:
1. FRONT view - showing frontal hairline and temples
2. LEFT view - showing left temple and side profile
3. RIGHT view - showing right temple and side profile

Provide a maximally precise, clinical diagnosis following the Norwood-Hamilton scale:

NORWOOD STAGES:
- Stage 1: No significant hair loss. Full juvenile hairline.
- Stage 2: Slight recession at temples. Mature/adult hairline. Triangular areas of recession.
- Stage 3: Deeper temporal recession. Bare or sparsely covered temples. M-shaped pattern.
- Stage 3 Vertex (3V): Stage 3 frontal with additional thinning at the vertex/crown.
- Stage 4: Further frontal recession than Stage 3. Vertex thinning. Hair band separates frontal and vertex.
- Stage 4A: Anterior variant - primarily frontal recession without distinct vertex involvement.
- Stage 5: Vertex and frontal regions larger, separating band narrower and sparser.
- Stage 5A: Anterior variant - hairline recession extends further back without distinct vertex.
- Stage 6: Bridge of hair separating front and vertex is gone. Single large bald area.
- Stage 6: Only lateral and posterior fringe remains.
- Stage 7: Most extensive. Only narrow horseshoe band of hair on sides and back.

VARIANTS:
- "A" (Anterior): Front-to-back recession without distinct vertex island
- "V" (Vertex): Distinct vertex involvement with maintained frontal band

Your assessment should be:
- Clinical and precise
- Reference specific observable features
- Explain differential diagnosis (why this stage vs adjacent stages)
- Confidence based on photo clarity and presentation consistency

This certification will be official documentation. Be thorough and accurate."""
```

### Tasks

**`app/tasks/certification.py`**
```python
"""Certification tasks."""
import logging
from datetime import datetime
from celery import shared_task

from app.llm import execute_vision_task
from app.llm.schemas.certification import PhotoValidationResult, CertificationDiagnosis
from app.llm.prompts.certification import PHOTO_VALIDATION_PROMPT, CERTIFICATION_DIAGNOSIS_PROMPT
from app.services.s3 import s3_service
from app.services.pdf import generate_certification_pdf
from app.db import SessionLocal
from app.models.certification import (
    Certification,
    CertificationPhoto,
    CertificationStatus,
    ValidationStatus,
    PhotoType,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def validate_certification_photo(
    self,
    photo_id: str,
    image_base64: str,
    content_type: str,
    photo_type: str,
):
    """Validate a certification photo for quality."""
    db = SessionLocal()
    try:
        photo = db.query(CertificationPhoto).filter(
            CertificationPhoto.id == photo_id
        ).first()

        if not photo:
            return {"success": False, "error": "Photo not found"}

        # Validate with LLM
        result = execute_vision_task(
            images=[(image_base64, content_type)],
            system_prompt=PHOTO_VALIDATION_PROMPT,
            response_model=PhotoValidationResult,
            user_text=f"Validate this {photo_type.upper()} photo for Norwood certification.",
        )

        # Update photo record
        photo.validation_status = (
            ValidationStatus.approved if result.approved
            else ValidationStatus.rejected
        )
        photo.rejection_reason = result.rejection_reason
        photo.quality_notes = result.quality_notes
        db.commit()

        return {
            "success": True,
            "approved": result.approved,
            "rejection_reason": result.rejection_reason,
            "quality_notes": result.quality_notes,
        }

    except Exception as e:
        logger.error(f"Photo validation failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def generate_certification_diagnosis(self, certification_id: str):
    """Generate final certification diagnosis from 3 validated photos."""
    db = SessionLocal()
    try:
        certification = db.query(Certification).filter(
            Certification.id == certification_id
        ).first()

        if not certification:
            return {"success": False, "error": "Certification not found"}

        certification.status = CertificationStatus.analyzing
        db.commit()

        # Get all approved photos
        photos = {
            p.photo_type: p for p in certification.photos
            if p.validation_status == ValidationStatus.approved
        }

        required = {PhotoType.front, PhotoType.left, PhotoType.right}
        if set(photos.keys()) != required:
            certification.status = CertificationStatus.failed
            db.commit()
            return {"success": False, "error": "Missing approved photos"}

        # Fetch images from S3
        images = []
        for photo_type in [PhotoType.front, PhotoType.left, PhotoType.right]:
            photo = photos[photo_type]
            image_data, content_type = s3_service.get_image_base64(photo.s3_key)
            images.append((image_data, content_type))

        # Generate diagnosis
        result = execute_vision_task(
            images=images,
            system_prompt=CERTIFICATION_DIAGNOSIS_PROMPT,
            response_model=CertificationDiagnosis,
            user_text="The images are in order: FRONT, LEFT, RIGHT. Provide the official Norwood certification diagnosis.",
        )

        # Update certification
        certification.norwood_stage = result.norwood_stage
        certification.norwood_variant = result.norwood_variant
        certification.confidence = result.confidence
        certification.clinical_assessment = result.clinical_assessment
        certification.observable_features = result.observable_features
        certification.differential_considerations = result.differential_considerations
        certification.certified_at = datetime.utcnow()

        # Generate PDF
        user = certification.user
        pdf_bytes = generate_certification_pdf(
            user_name=user.name or user.email,
            norwood_stage=result.norwood_stage,
            norwood_variant=result.norwood_variant,
            confidence=result.confidence,
            clinical_assessment=result.clinical_assessment,
            certified_at=certification.certified_at,
        )

        # Upload PDF to S3
        pdf_key = s3_service.upload_pdf(
            pdf_bytes,
            certification.user_id,
            f"certification_{certification.id}.pdf"
        )
        certification.pdf_s3_key = pdf_key
        certification.status = CertificationStatus.completed
        db.commit()

        return {
            "success": True,
            "norwood_stage": result.norwood_stage,
            "norwood_variant": result.norwood_variant,
            "confidence": result.confidence,
        }

    except Exception as e:
        logger.error(f"Certification diagnosis failed: {e}", exc_info=True)
        if certification:
            certification.status = CertificationStatus.failed
            db.commit()
        return {"success": False, "error": str(e)}
    finally:
        db.close()
```

### PDF Service

**`app/services/pdf.py`**
```python
"""PDF generation for certifications."""
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os

# Colors
GOLD = HexColor("#C9A227")
NAVY = HexColor("#1a365d")
DARK_GRAY = HexColor("#2d3748")

# Paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SEAL_PATH = os.path.join(ASSETS_DIR, "seal.png")
SIGNATURE_PATH = os.path.join(ASSETS_DIR, "signature.png")


def generate_certification_pdf(
    user_name: str,
    norwood_stage: int,
    norwood_variant: str | None,
    confidence: float,
    clinical_assessment: str,
    certified_at: datetime,
) -> bytes:
    """Generate university-style certification PDF."""

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Draw ornate border
    _draw_border(c, width, height)

    # Header
    c.setFont("Times-Bold", 28)
    c.setFillColor(NAVY)
    c.drawCentredString(width / 2, height - 1.5 * inch, "CERTIFICATE OF NORWOOD CLASSIFICATION")

    # Subtitle
    c.setFont("Times-Italic", 14)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 2 * inch, "Official Hair Loss Assessment")

    # Decorative line
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(1.5 * inch, height - 2.3 * inch, width - 1.5 * inch, height - 2.3 * inch)

    # "This certifies that"
    c.setFont("Times-Roman", 12)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 3 * inch, "This is to certify that")

    # Name
    c.setFont("Times-Bold", 24)
    c.setFillColor(NAVY)
    c.drawCentredString(width / 2, height - 3.5 * inch, user_name)

    # Decorative line under name
    name_width = c.stringWidth(user_name, "Times-Bold", 24)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(
        (width - name_width) / 2 - 20, height - 3.6 * inch,
        (width + name_width) / 2 + 20, height - 3.6 * inch
    )

    # "has been officially classified as"
    c.setFont("Times-Roman", 12)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 4.1 * inch, "has been officially classified as")

    # Norwood Stage (big)
    stage_text = f"NORWOOD STAGE {norwood_stage}"
    if norwood_variant:
        stage_text += norwood_variant
    c.setFont("Times-Bold", 36)
    c.setFillColor(NAVY)
    c.drawCentredString(width / 2, height - 4.8 * inch, stage_text)

    # Confidence
    confidence_pct = int(confidence * 100)
    c.setFont("Times-Italic", 11)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 5.2 * inch, f"Classification Confidence: {confidence_pct}%")

    # Clinical assessment box
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.5)
    c.rect(1 * inch, height - 7.5 * inch, width - 2 * inch, 1.8 * inch)

    c.setFont("Times-Bold", 10)
    c.setFillColor(NAVY)
    c.drawString(1.2 * inch, height - 5.9 * inch, "CLINICAL ASSESSMENT")

    # Wrap and draw clinical assessment text
    c.setFont("Times-Roman", 9)
    c.setFillColor(DARK_GRAY)
    _draw_wrapped_text(
        c,
        clinical_assessment,
        1.2 * inch,
        height - 6.2 * inch,
        width - 2.4 * inch,
        12
    )

    # Date
    date_str = certified_at.strftime("%B %d, %Y")
    c.setFont("Times-Roman", 11)
    c.drawCentredString(width / 2, height - 8 * inch, f"Certified on {date_str}")

    # Signature section
    sig_y = height - 9.2 * inch

    # Signature line
    c.setStrokeColor(DARK_GRAY)
    c.setLineWidth(0.5)
    c.line(1.5 * inch, sig_y, 3.5 * inch, sig_y)

    # Signature image (placeholder)
    if os.path.exists(SIGNATURE_PATH):
        sig_img = ImageReader(SIGNATURE_PATH)
        c.drawImage(sig_img, 1.8 * inch, sig_y + 0.1 * inch, width=1.5 * inch, height=0.5 * inch, mask='auto')

    c.setFont("Times-Roman", 9)
    c.drawString(1.5 * inch, sig_y - 0.25 * inch, "President & Founder")
    c.drawString(1.5 * inch, sig_y - 0.45 * inch, "Norwood AI")

    # Seal
    seal_x = width - 2.5 * inch
    if os.path.exists(SEAL_PATH):
        seal_img = ImageReader(SEAL_PATH)
        c.drawImage(seal_img, seal_x, sig_y - 0.5 * inch, width=1.2 * inch, height=1.2 * inch, mask='auto')
    else:
        # Draw placeholder seal
        _draw_placeholder_seal(c, seal_x + 0.6 * inch, sig_y + 0.1 * inch)

    # Footer
    c.setFont("Times-Italic", 8)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, 0.5 * inch, "This certificate is for educational and entertainment purposes only. Not a medical diagnosis.")

    c.save()
    buffer.seek(0)
    return buffer.read()


def _draw_border(c, width, height):
    """Draw ornate double border."""
    margin = 0.5 * inch

    # Outer border
    c.setStrokeColor(GOLD)
    c.setLineWidth(3)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Inner border
    c.setLineWidth(1)
    inner_margin = 0.7 * inch
    c.rect(inner_margin, inner_margin, width - 2 * inner_margin, height - 2 * inner_margin)

    # Corner flourishes (simple L shapes)
    flourish_size = 0.3 * inch
    c.setLineWidth(2)

    # Top-left
    c.line(margin + 0.1 * inch, height - margin - 0.1 * inch,
           margin + 0.1 * inch + flourish_size, height - margin - 0.1 * inch)
    c.line(margin + 0.1 * inch, height - margin - 0.1 * inch,
           margin + 0.1 * inch, height - margin - 0.1 * inch - flourish_size)

    # Top-right
    c.line(width - margin - 0.1 * inch, height - margin - 0.1 * inch,
           width - margin - 0.1 * inch - flourish_size, height - margin - 0.1 * inch)
    c.line(width - margin - 0.1 * inch, height - margin - 0.1 * inch,
           width - margin - 0.1 * inch, height - margin - 0.1 * inch - flourish_size)

    # Bottom-left
    c.line(margin + 0.1 * inch, margin + 0.1 * inch,
           margin + 0.1 * inch + flourish_size, margin + 0.1 * inch)
    c.line(margin + 0.1 * inch, margin + 0.1 * inch,
           margin + 0.1 * inch, margin + 0.1 * inch + flourish_size)

    # Bottom-right
    c.line(width - margin - 0.1 * inch, margin + 0.1 * inch,
           width - margin - 0.1 * inch - flourish_size, margin + 0.1 * inch)
    c.line(width - margin - 0.1 * inch, margin + 0.1 * inch,
           width - margin - 0.1 * inch, margin + 0.1 * inch + flourish_size)


def _draw_placeholder_seal(c, x, y):
    """Draw a placeholder seal circle."""
    c.setStrokeColor(GOLD)
    c.setFillColor(HexColor("#f7f3e8"))
    c.setLineWidth(2)
    c.circle(x, y, 0.5 * inch, fill=1)

    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 8)
    c.drawCentredString(x, y + 0.1 * inch, "NORWOOD")
    c.drawCentredString(x, y - 0.1 * inch, "AI")


def _draw_wrapped_text(c, text, x, y, max_width, line_height):
    """Draw text wrapped to max_width."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        if c.stringWidth(test_line, "Times-Roman", 9) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    for i, line in enumerate(lines[:8]):  # Max 8 lines
        c.drawString(x, y - (i * line_height), line)
```

### Router

**`app/routers/certification.py`**
```python
"""Certification API endpoints."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import get_current_user, require_auth
from app.models.user import User
from app.models.certification import (
    Certification,
    CertificationPhoto,
    CertificationStatus,
    ValidationStatus,
    PhotoType,
)
from app.services.s3 import s3_service
from app.tasks.certification import validate_certification_photo, generate_certification_diagnosis

router = APIRouter(prefix="/api/certification", tags=["certification"])


# --- Schemas ---

class StartCertificationResponse(BaseModel):
    certification_id: str
    status: str


class PhotoUploadRequest(BaseModel):
    image_base64: str
    content_type: str


class PhotoUploadResponse(BaseModel):
    photo_id: str
    task_id: str


class PhotoStatusResponse(BaseModel):
    photo_id: str
    photo_type: str
    validation_status: str
    rejection_reason: str | None
    quality_notes: str | None


class CertificationStatusResponse(BaseModel):
    certification_id: str
    status: str
    photos: list[PhotoStatusResponse]
    norwood_stage: int | None
    norwood_variant: str | None
    confidence: float | None
    clinical_assessment: str | None
    pdf_url: str | None
    certified_at: datetime | None


class DiagnoseResponse(BaseModel):
    task_id: str


# --- Dependencies ---

def require_premium(user: User = Depends(require_auth)) -> User:
    """Require premium or admin access."""
    if not user.is_premium and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Premium subscription required for certification"
        )
    return user


def check_certification_cooldown(user: User, db: Session) -> None:
    """Check if user can create a new certification (1 per month)."""
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    recent = db.query(Certification).filter(
        Certification.user_id == user.id,
        Certification.status == CertificationStatus.completed,
        Certification.certified_at >= one_month_ago,
    ).first()

    if recent and not user.is_admin:
        days_until = 30 - (datetime.utcnow() - recent.certified_at).days
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You can only certify once per month. {days_until} days remaining."
        )


# --- Endpoints ---

@router.post("/start", response_model=StartCertificationResponse)
def start_certification(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Start a new certification process."""
    check_certification_cooldown(user, db)

    # Check for incomplete certifications
    incomplete = db.query(Certification).filter(
        Certification.user_id == user.id,
        Certification.status.in_([
            CertificationStatus.photos_pending,
            CertificationStatus.analyzing,
        ])
    ).first()

    if incomplete:
        # Return existing incomplete certification
        return StartCertificationResponse(
            certification_id=incomplete.id,
            status=incomplete.status.value,
        )

    # Create new certification
    certification = Certification(user_id=user.id)
    db.add(certification)
    db.commit()
    db.refresh(certification)

    return StartCertificationResponse(
        certification_id=certification.id,
        status=certification.status.value,
    )


@router.post("/{cert_id}/photo/{photo_type}", response_model=PhotoUploadResponse)
def upload_photo(
    cert_id: str,
    photo_type: PhotoType,
    request: PhotoUploadRequest,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Upload and validate a certification photo."""
    certification = db.query(Certification).filter(
        Certification.id == cert_id,
        Certification.user_id == user.id,
    ).first()

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    if certification.status != CertificationStatus.photos_pending:
        raise HTTPException(status_code=400, detail="Certification is not accepting photos")

    # Check if photo type already exists and is approved
    existing = db.query(CertificationPhoto).filter(
        CertificationPhoto.certification_id == cert_id,
        CertificationPhoto.photo_type == photo_type,
    ).first()

    if existing and existing.validation_status == ValidationStatus.approved:
        raise HTTPException(
            status_code=400,
            detail=f"{photo_type.value} photo already approved"
        )

    # Delete existing photo if retaking
    if existing:
        s3_service.delete_image(existing.s3_key)
        db.delete(existing)
        db.commit()

    # Upload to S3
    s3_key = s3_service.upload_base64_image(
        request.image_base64,
        user.id,
        request.content_type,
        prefix=f"certifications/{cert_id}",
    )

    # Create photo record
    photo = CertificationPhoto(
        certification_id=cert_id,
        photo_type=photo_type,
        s3_key=s3_key,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)

    # Queue validation task
    task = validate_certification_photo.delay(
        photo.id,
        request.image_base64,
        request.content_type,
        photo_type.value,
    )

    return PhotoUploadResponse(
        photo_id=photo.id,
        task_id=task.id,
    )


@router.get("/{cert_id}/status", response_model=CertificationStatusResponse)
def get_certification_status(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get current certification status."""
    certification = db.query(Certification).filter(
        Certification.id == cert_id,
        Certification.user_id == user.id,
    ).first()

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    photos = [
        PhotoStatusResponse(
            photo_id=p.id,
            photo_type=p.photo_type.value,
            validation_status=p.validation_status.value,
            rejection_reason=p.rejection_reason,
            quality_notes=p.quality_notes,
        )
        for p in certification.photos
    ]

    pdf_url = None
    if certification.pdf_s3_key:
        pdf_url = s3_service.get_presigned_url(certification.pdf_s3_key)

    return CertificationStatusResponse(
        certification_id=certification.id,
        status=certification.status.value,
        photos=photos,
        norwood_stage=certification.norwood_stage,
        norwood_variant=certification.norwood_variant,
        confidence=certification.confidence,
        clinical_assessment=certification.clinical_assessment,
        pdf_url=pdf_url,
        certified_at=certification.certified_at,
    )


@router.post("/{cert_id}/diagnose", response_model=DiagnoseResponse)
def trigger_diagnosis(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Trigger final diagnosis after all photos are approved."""
    certification = db.query(Certification).filter(
        Certification.id == cert_id,
        Certification.user_id == user.id,
    ).first()

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    if certification.status != CertificationStatus.photos_pending:
        raise HTTPException(status_code=400, detail="Certification already processing or complete")

    # Check all photos are approved
    approved_types = {
        p.photo_type for p in certification.photos
        if p.validation_status == ValidationStatus.approved
    }
    required = {PhotoType.front, PhotoType.left, PhotoType.right}

    if approved_types != required:
        missing = required - approved_types
        raise HTTPException(
            status_code=400,
            detail=f"Missing approved photos: {[t.value for t in missing]}"
        )

    # Queue diagnosis task
    task = generate_certification_diagnosis.delay(certification.id)

    return DiagnoseResponse(task_id=task.id)


@router.get("/{cert_id}/pdf")
def download_pdf(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get presigned URL for PDF download."""
    certification = db.query(Certification).filter(
        Certification.id == cert_id,
        Certification.user_id == user.id,
    ).first()

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    if not certification.pdf_s3_key:
        raise HTTPException(status_code=404, detail="PDF not yet generated")

    url = s3_service.get_presigned_url(certification.pdf_s3_key, expires_in=3600)
    return {"pdf_url": url}


@router.get("/history")
def get_certification_history(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get user's certification history."""
    certifications = db.query(Certification).filter(
        Certification.user_id == user.id,
        Certification.status == CertificationStatus.completed,
    ).order_by(Certification.certified_at.desc()).all()

    return [
        {
            "id": c.id,
            "norwood_stage": c.norwood_stage,
            "norwood_variant": c.norwood_variant,
            "certified_at": c.certified_at,
            "pdf_url": s3_service.get_presigned_url(c.pdf_s3_key) if c.pdf_s3_key else None,
        }
        for c in certifications
    ]
```

### Frontend View

**`frontend/src/views/Certification.vue`** (outline)
```vue
<template>
  <div class="certification-container">
    <!-- Premium gate -->
    <div v-if="!isPremium" class="upgrade-prompt">
      <h2>Premium Feature</h2>
      <p>Norwood Certification requires a premium subscription.</p>
      <button @click="goToSettings">Upgrade Now</button>
    </div>

    <!-- Cooldown message -->
    <div v-else-if="cooldownDays > 0" class="cooldown-message">
      <h2>Certification Cooldown</h2>
      <p>You can certify again in {{ cooldownDays }} days.</p>
    </div>

    <!-- Step wizard -->
    <div v-else class="wizard">
      <div class="steps">
        <div :class="['step', { active: step === 1, done: step > 1 }]">Front</div>
        <div :class="['step', { active: step === 2, done: step > 2 }]">Left</div>
        <div :class="['step', { active: step === 3, done: step > 3 }]">Right</div>
        <div :class="['step', { active: step === 4 }]">Certificate</div>
      </div>

      <!-- Photo upload for steps 1-3 -->
      <div v-if="step <= 3" class="upload-section">
        <h3>Upload {{ currentPhotoType }} Photo</h3>
        <p class="instructions">{{ photoInstructions[currentPhotoType] }}</p>

        <input type="file" accept="image/*" @change="handleFileSelect" />
        <img v-if="preview" :src="preview" class="preview" />

        <button v-if="preview && !validating" @click="uploadPhoto">
          Submit for Validation
        </button>

        <div v-if="validating" class="validating">
          Validating photo...
        </div>

        <div v-if="validationResult" :class="['result', validationResult.approved ? 'approved' : 'rejected']">
          <template v-if="validationResult.approved">
            ✓ Photo approved! {{ validationResult.quality_notes }}
          </template>
          <template v-else>
            ✗ Photo rejected: {{ validationResult.rejection_reason }}
            <button @click="retake">Retake Photo</button>
          </template>
        </div>

        <button v-if="validationResult?.approved" @click="nextStep">
          Continue
        </button>
      </div>

      <!-- Final step - generate certificate -->
      <div v-if="step === 4" class="certificate-section">
        <div v-if="!certification?.norwood_stage">
          <h3>All Photos Approved!</h3>
          <p>Ready to generate your official Norwood certification.</p>
          <button @click="generateCertificate" :disabled="generating">
            {{ generating ? 'Generating...' : 'Generate Certificate' }}
          </button>
        </div>

        <div v-else class="certificate-result">
          <h2>🎓 Certification Complete!</h2>
          <div class="stage-display">
            Norwood Stage {{ certification.norwood_stage }}{{ certification.norwood_variant || '' }}
          </div>
          <p class="confidence">Confidence: {{ (certification.confidence * 100).toFixed(0) }}%</p>
          <p class="assessment">{{ certification.clinical_assessment }}</p>

          <a :href="certification.pdf_url" target="_blank" class="download-btn">
            Download PDF Certificate
          </a>

          <!-- Future: LinkedIn share button -->
        </div>
      </div>
    </div>
  </div>
</template>
```

### Update AppHeader.vue

Add "Certification" link between Counseling and Settings, with premium badge indicator.

### Update main.py

```python
from app.routers import certification

app.include_router(certification.router)
```

### Update celery_worker.py

```python
celery_app.conf.imports = [
    "app.tasks.analyze",
    "app.tasks.counseling",
    "app.tasks.certification",  # Add this
]
```

---

## File Changes Summary

| Action | File |
|--------|------|
| CREATE | `app/llm/__init__.py` |
| CREATE | `app/llm/client.py` |
| CREATE | `app/llm/executor.py` |
| CREATE | `app/llm/schemas/__init__.py` |
| CREATE | `app/llm/schemas/base.py` |
| CREATE | `app/llm/schemas/analysis.py` |
| CREATE | `app/llm/schemas/counseling.py` |
| CREATE | `app/llm/schemas/certification.py` |
| CREATE | `app/llm/prompts/__init__.py` |
| CREATE | `app/llm/prompts/analysis.py` |
| CREATE | `app/llm/prompts/counseling.py` |
| CREATE | `app/llm/prompts/certification.py` |
| REFACTOR | `app/tasks/analyze.py` |
| REFACTOR | `app/tasks/counseling.py` |
| CREATE | `app/models/certification.py` |
| MODIFY | `app/models/__init__.py` |
| MODIFY | `app/models/user.py` |
| CREATE | `app/routers/certification.py` |
| MODIFY | `app/main.py` |
| MODIFY | `app/celery_worker.py` |
| CREATE | `app/services/pdf.py` |
| CREATE | `app/tasks/certification.py` |
| CREATE | `app/assets/` (placeholder images) |
| CREATE | `migrations/005_certification.sql` |
| CREATE | `frontend/src/views/Certification.vue` |
| MODIFY | `frontend/src/router/index.js` |
| MODIFY | `frontend/src/components/AppHeader.vue` |

---

## Dependencies to Add

**Backend (pyproject.toml):**
```toml
reportlab = "^4.0"  # PDF generation
```

---

## Testing Plan

1. LLM executor unit tests with mocked Anthropic client
2. Photo validation integration test (upload → validate → approve/reject)
3. Full certification flow E2E test
4. PDF generation visual inspection
5. Cooldown enforcement test
6. Premium gate test (non-premium user blocked)
