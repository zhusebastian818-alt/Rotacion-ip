"""Aggregator and base connectors utilizing modular regional connector modules (CABA, PBA, SINAI, Córdoba, Santa Fe)."""

import logging
from app.services.connectors.base import BaseConnector, ConnectorError
from app.services.connectors.caba import CABAConnector
from app.services.connectors.pba import PBAConnector
from app.services.connectors.sinai import SINAIConnector
from app.services.connectors.cordoba import CordobaConnector
from app.services.connectors.santa_fe import SantaFeConnector
from app.services.connectors.national_monitor import NationalMonitorConnector

logger = logging.getLogger(__name__)


class MunicipalScraperConnector(BaseConnector):
    """Simulated connector for Municipalities (e.g., Vicente López, San Isidro, La Matanza)."""
    
    def __init__(self, municipality_name: str):
        self.municipality_name = municipality_name
        self.jurisdiction_name = f"Municipalidad - {municipality_name}"

    async def fetch_fines(self, plate_number: str):
        import asyncio, random
        from datetime import datetime, timezone, timedelta
        from app.models.fine import FineRecord, FineStatus
        
        logger.info("Connecting to Municipal Portal of %s for plate %s", self.municipality_name, plate_number)
        try:
            async with asyncio.timeout(3.0):
                await asyncio.sleep(0.2)
                fines = []
                if hash(plate_number + self.municipality_name) % 3 == 0:
                    now = datetime.now(timezone.utc)
                    fines.append(
                        FineRecord(
                            fine_id=f"MUN-{self.municipality_name[:3].upper()}-{random.randint(1000, 9999)}",
                            plate_number=plate_number,
                            infraction_code="MUN-SEM-02",
                            issue_date=now - timedelta(days=random.randint(2, 30)),
                            amount=18200.00,
                            currency="ARS",
                            status=FineStatus.PENDING,
                            authority=f"Municipalidad de {self.municipality_name} - Tribunal de Faltas",
                            description="Cruce de semáforo en rojo registrado por cámara municipal.",
                        )
                    )
                return fines
        except asyncio.TimeoutError:
            return [
                FineRecord(
                    fine_id="MUN-ERR-FALLBACK",
                    plate_number=plate_number,
                    infraction_code="SYS-UNAVAILABLE",
                    issue_date=datetime.now(timezone.utc),
                    amount=0.0,
                    currency="ARS",
                    status=FineStatus.PENDING,
                    authority=f"Municipalidad de {self.municipality_name} (SISTEMA DEGRADADO)",
                    description="AVISO: Portal municipal temporalmente no disponible por timeout.",
                )
            ]


class NationalFineAggregator(NationalMonitorConnector):
    """Backward-compatible alias for NationalMonitorConnector used across existing fine monitor services."""
    pass
