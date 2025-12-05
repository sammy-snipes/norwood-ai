from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field


class NorwoodAnalysis(BaseModel):
    """Response schema for Norwood scale analysis."""

    stage: str = Field(
        ...,
        description="Norwood stage classification (e.g., '1', '2', '3', '3V', '4', '5', '6', '7')",
    )
    confidence: str = Field(
        ...,
        description="Confidence level: 'high', 'medium', or 'low'",
    )
    description: str = Field(
        ...,
        description="Brief description of their hair situation",
    )
    reasoning: str = Field(
        ...,
        description="What was observed in the image",
    )
    title: str = Field(
        ...,
        description="Short punchy title (5 words or less)",
    )
    analysis_text: str = Field(
        ...,
        validation_alias=AliasChoices("analysis_text", "reflection", "roast"),
        description="Philosophical reflection on the hair situation",
    )


class AnalyzeResponse(BaseModel):
    """API response wrapper for analysis endpoint."""

    success: bool = Field(..., description="Whether the analysis was successful")
    analysis: NorwoodAnalysis | None = Field(
        None, description="The Norwood analysis result, if successful"
    )
    error: str | None = Field(None, description="Error message, if analysis failed")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")


class TaskResponse(BaseModel):
    """Response when submitting a new analysis task."""

    task_id: str = Field(..., description="Unique task identifier for polling")
    status: str = Field(..., description="Initial task status")


class TaskStatusResponse(BaseModel):
    """Response when polling for task status."""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status: pending, started, completed, failed")
    ready: bool = Field(..., description="Whether the task has completed")
    result: AnalyzeResponse | None = Field(None, description="Analysis result if completed")
    error: str | None = Field(None, description="Error message if failed")


# Payment Schemas
class CheckoutSessionResponse(BaseModel):
    """Response from creating a Stripe checkout session."""

    checkout_url: str = Field(..., description="Stripe Checkout URL to redirect user to")


class PaymentRecord(BaseModel):
    """Individual payment record."""

    id: str = Field(..., description="Payment ID")
    stripe_payment_id: str = Field(..., description="Stripe payment intent ID")
    amount_cents: int = Field(..., description="Amount paid in cents")
    status: str = Field(..., description="Payment status: pending, succeeded, failed")
    created_at: datetime = Field(..., description="Payment creation timestamp")

    model_config = {"from_attributes": True}


class PaymentStatusResponse(BaseModel):
    """User's premium status and payment history."""

    is_premium: bool = Field(..., description="Whether user has premium access")
    payments: list[PaymentRecord] = Field(..., description="List of user's payments")


class AnalysisHistoryItem(BaseModel):
    """A single analysis in the user's history."""

    id: str = Field(..., description="Analysis ID")
    norwood_stage: int = Field(..., description="Norwood stage (1-7)")
    confidence: str = Field(..., description="Confidence level")
    title: str = Field(..., description="Short title")
    analysis_text: str = Field(..., description="The analysis text")
    reasoning: str | None = Field(None, description="Analysis reasoning")
    image_url: str | None = Field(None, description="S3 URL of the image")
    created_at: datetime = Field(..., description="When the analysis was created")

    model_config = {"from_attributes": True}
