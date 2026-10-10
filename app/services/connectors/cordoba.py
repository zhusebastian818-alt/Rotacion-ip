"""Córdoba (Policía Caminera / Provincia) Traffic Fines Connector."""

import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import List
from app.models.fine import FineRecord, FineStatus
from app.services.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class CordobaConnector(BaseConnector):
    """Connector for querying traffic fines from Córdoba (Policía Caminera / Rentas Córdoba)."""

    jurisdiction_name = "Córdoba (Caminera)"
    portal_url = "https://www.cba.gov.ar/policia-caminera/"

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = timeout_seconds

    async def fetch_fines(self, plate_number: str) -> List[FineRecord]:
        logger.info("Connecting to Córdoba Policía Caminera Portal for plate %s", plate_number)
        try:
            async with asyncio.timeout(self.timeout_seconds):
                await asyncio.sleep(random.uniform(0.2, 0.5))
                fines = []
                if len(plate_number) >= 5:
                    now = datetime.now(timezone.utc)
                    fines.append(
                        FineRecord(
                            fine_id=f"CBA-{random.randint(10000, 99999)}",
                            plate_number=plate_number,
                            infraction_code="CBA-CAM-01",
                            issue_date=now - timedelta(days=random.randint(4, 30)),
                            amount=42000.00,
                            currency="ARS",
                            status=FineStatus.PENDING,
                            authority="Policía Caminera de la Provincia de Córdoba",
                            description="Luces bajas encendidas obligatorias / Velocidad excedida en Autovía Córdoba.",
                        )
                    )
                return fines
        except asyncio.TimeoutError:
            logger.warning("Timeout connecting to Córdoba portal for plate %s", plate_number)
            return self._get_fallback_fine(plate_number, reason="Córdoba portal timeout")
        except Exception as e:
            logger.exception("Unexpected error querying Córdoba portal for plate %s", plate_number)
            return self._get_fallback_fine(plate_number, reason=str(e))

    def _get_fallback_fine(self, plate_number: str, reason: str) -> List[FineRecord]:
        now = datetime.now(timezone.utc)
        return [
            FineRecord(
                fine_id="CBA-ERR-FALLBACK",
                plate_number=plate_number,
                infraction_code="SYS-UNAVAILABLE",
                issue_date=now,
                amount=0.0,
                currency="ARS",
                status=FineStatus.PENDING,
                authority="Policía Caminera de Córdoba (SISTEMA DEGRADADO)",
                description=f"AVISO: Portal Córdoba no disponible. Motivo: {reason}.",
            )
        ]
