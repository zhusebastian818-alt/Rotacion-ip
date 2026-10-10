"""Fine domain models and input sanitization schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class FineStatus(str, Enum):
    """Lifecycle status of a detected traffic fine."""
    PENDING = "PENDING"
    PAID = "PAID"
    CONTESTED = "CONTESTED"
    DISMISSED = "DISMISSED"


class VehicleQueryRequest(BaseModel):
    """Vehicle query request payload with strict input sanitization."""
    plate_number: str = Field(
        ...,
        min_length=3,
        max_length=12,
        pattern=r"^[A-Za-z0-9\-]+$",
        description="License plate number sanitized against injection",
        examples=["ABC1234", "AA123BB"],
    )
    country_code: str = Field(
        default="AR",
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        description="ISO 3166-1 alpha-2 country code",
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        max_length=50,
        pattern=r"^[A-Za-z0-9\s\-]*$",
        description="Optional regional jurisdiction or province",
    )


class FineRecord(BaseModel):
    """Detailed fine infraction schema."""
    fine_id: str = Field(..., description="Unique provider infraction identifier")
    plate_number: str
    infraction_code: str
    issue_date: datetime
    amount: float = Field(..., ge=0.0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: FineStatus
    authority: str
    description: str


class VehicleFinesResponse(BaseModel):
    """Aggregate fines report for a single vehicle."""
    plate_number: str
    country_code: str
    total_fines: int
    total_amount: float
    currency: str
    fines: List[FineRecord]
    queried_at: datetime


class FleetBatchQueryRequest(BaseModel):
    """Batch fine monitoring request for B2B fleet management with anti-DoS bounds."""
    client_id: Optional[str] = Field(default="DIRECT-USER", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")
    vehicles: List[VehicleQueryRequest] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Fleet vehicles list bounded to max 50 to mitigate DoS",
    )


class BatchPlatesRequest(BaseModel):
    """Request payload containing a list of license plates for batch check & Excel report."""
    plates: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of license plates to query across CABA and Provincia de Buenos Aires.",
        examples=[["AA123BB", "AB456CD", "XYZ789"]],
    )


class FleetBatchQueryResponse(BaseModel):
    """Batch result for fleet monitoring."""
    batch_id: str
    client_id: str
    total_vehicles_processed: int
    total_infractions_found: int
    total_amount_due: float
    currency: str
    results: List[VehicleFinesResponse]
    processed_at: datetime
