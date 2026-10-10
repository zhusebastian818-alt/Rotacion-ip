"""Service layer handling fine querying and fleet monitoring aggregation using regional scrapers."""

import uuid
import logging
from datetime import datetime, timezone
from typing import List
from app.models.fine import (
    FineRecord,
    FineStatus,
    VehicleQueryRequest,
    VehicleFinesResponse,
    FleetBatchQueryRequest,
    FleetBatchQueryResponse,
)
from app.services.connectors import NationalFineAggregator

logger = logging.getLogger(__name__)


class FineMonitorService:
    """Core domain service for querying and aggregating vehicle fines across Argentine jurisdictions."""

    def __init__(self):
        self.national_aggregator = NationalFineAggregator()

    @staticmethod
    def sanitize_plate(plate: str) -> str:
        """Normalize plate format to uppercase without extraneous spaces."""
        return plate.strip().upper().replace(" ", "")

    async def query_vehicle_fines(self, query: VehicleQueryRequest) -> VehicleFinesResponse:
        """Fetch fines for a specific vehicle across CABA, PBA, and Municipalities."""
        normalized_plate = self.sanitize_plate(query.plate_number)
        logger.info(
            "Querying national fines for vehicle",
            extra={"plate": normalized_plate, "country": query.country_code},
        )

        fines: List[FineRecord] = []
        now = datetime.now(timezone.utc)

        if query.country_code.upper() == "AR":
            # Query real scrapers/connectors for Argentina
            fines = await self.national_aggregator.fetch_all_jurisdictions(normalized_plate)
        else:
            # Fallback or generic mock for other countries / 'FINE' trigger
            if "FINE" in normalized_plate:
                fines.append(
                    FineRecord(
                        fine_id=f"FN-{uuid.uuid4().hex[:8].upper()}",
                        plate_number=normalized_plate,
                        infraction_code="SPD-001",
                        issue_date=now,
                        amount=150.0,
                        currency="USD",
                        status=FineStatus.PENDING,
                        authority="Metropolitan Transit Safety Authority",
                        description="Excess speed detected by automated radar camera.",
                    )
                )

        total_amount = sum(f.amount for f in fines)
        currency = "ARS" if query.country_code.upper() == "AR" else "USD"

        return VehicleFinesResponse(
            plate_number=normalized_plate,
            country_code=query.country_code,
            total_fines=len(fines),
            total_amount=total_amount,
            currency=currency,
            fines=fines,
            queried_at=now,
        )

    async def batch_monitor_fleet(
        self, batch_request: FleetBatchQueryRequest
    ) -> FleetBatchQueryResponse:
        """Process multiple vehicles for enterprise B2B fleet monitoring."""
        results: List[VehicleFinesResponse] = []
        total_infractions = 0
        total_amount = 0.0
        currency = "ARS"

        for vehicle in batch_request.vehicles:
            res = await self.query_vehicle_fines(vehicle)
            results.append(res)
            total_infractions += res.total_fines
            total_amount += res.total_amount
            currency = res.currency

        return FleetBatchQueryResponse(
            batch_id=f"BATCH-{uuid.uuid4().hex[:12].upper()}",
            client_id=batch_request.client_id,
            total_vehicles_processed=len(batch_request.vehicles),
            total_infractions_found=total_infractions,
            total_amount_due=round(total_amount, 2),
            currency=currency,
            results=results,
            processed_at=datetime.now(timezone.utc),
        )
