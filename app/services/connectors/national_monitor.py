"""Unified National Monitor Connector.
Executes concurrent parallel queries across CABA, PBA, SINAI (Agencia Nacional),
Córdoba, Santa Fe, and key municipalities, grouping all detected fines.
"""

import asyncio
import logging
from typing import List, Dict, Any
from app.models.fine import FineRecord
from app.services.connectors.caba import CABAConnector
from app.services.connectors.pba import PBAConnector
from app.services.connectors.sinai import SINAIConnector
from app.services.connectors.cordoba import CordobaConnector
from app.services.connectors.santa_fe import SantaFeConnector
from app.services.connectors.base import BaseConnector

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


class NationalMonitorConnector:
    """Unified monitor that queries CABA, PBA, SINAI, Córdoba, Santa Fe, and municipalities in parallel."""

    def __init__(self):
        self.connectors = [
            CABAConnector(),
            PBAConnector(),
            SINAIConnector(),
            CordobaConnector(),
            SantaFeConnector(),
            MunicipalScraperConnector("Vicente López"),
            MunicipalScraperConnector("San Isidro"),
            MunicipalScraperConnector("La Matanza"),
        ]

    async def fetch_all_regions(self, plate_number: str) -> List[FineRecord]:
        """Execute parallel queries across all registered regional & national connectors."""
        logger.info("Executing parallel national monitoring queries for plate %s across %d jurisdictions", plate_number, len(self.connectors))
        
        tasks = [connector.fetch_fines(plate_number) for connector in self.connectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_fines: List[FineRecord] = []
        for idx, res in enumerate(results):
            connector_name = self.connectors[idx].jurisdiction_name
            if isinstance(res, list):
                logger.info("Connector [%s] returned %d fine(s)", connector_name, len(res))
                all_fines.extend(res)
            elif isinstance(res, Exception):
                logger.error("Connector [%s] failed with exception: %s", connector_name, str(res))

        return all_fines

    async def fetch_grouped_report(self, plate_number: str) -> Dict[str, Any]:
        """Fetch all fines and group/summarize them by jurisdiction and status for web screens & reports."""
        fines = await self.fetch_all_regions(plate_number)
        
        total_amount = sum(f.amount for f in fines)
        pending_count = sum(1 for f in fines if f.status.value == "PENDING")
        
        by_jurisdiction: Dict[str, List[FineRecord]] = {}
        for fine in fines:
            # Group by authority/jurisdiction key
            auth = fine.authority or "Desconocida"
            if auth not in by_jurisdiction:
                by_jurisdiction[auth] = []
            by_jurisdiction[auth].append(fine)

        return {
            "plate_number": plate_number,
            "total_fines": len(fines),
            "total_amount": total_amount,
            "pending_count": pending_count,
            "fines": fines,
            "by_jurisdiction": by_jurisdiction,
        }
