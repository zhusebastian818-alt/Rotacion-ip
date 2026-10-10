"""SQLAlchemy ORM model for Traffic Fines linked with Tenants."""

from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.fine import FineStatus


class FineRecordModel(Base):
    """Represents a traffic infraction record registered for a vehicle under a tenant."""

    __tablename__ = "fine_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fine_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plate_number: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="AR")
    infraction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    province: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    municipality: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    issuing_authority: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[FineStatus] = mapped_column(SQLEnum(FineStatus), nullable=False, default=FineStatus.PENDING)
    authority: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship back to Tenant
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="fines")

    __table_args__ = (
        Index("idx_tenant_plate", "tenant_id", "plate_number"),
        Index("idx_status_issue_date", "status", "issue_date"),
    )

    def __repr__(self) -> str:
        return f"<FineRecordModel(fine_id={self.fine_id}, plate={self.plate_number}, status={self.status}, amount={self.amount})>"
