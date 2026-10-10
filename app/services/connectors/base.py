"""Base class and shared exceptions for regional traffic fine connectors."""

import logging
from typing import List
from app.models.fine import FineRecord

logger = logging.getLogger(__name__)


class ConnectorError(Exception):
    """Base exception for regional connector failures."""
    pass


class BaseConnector:
    """Abstract base class for all regional and national traffic fine connectors/scrapers."""

    jurisdiction_name: str = "Base"
    portal_url: str = ""

    async def fetch_fines(self, plate_number: str) -> List[FineRecord]:
        """Fetch traffic fines for a given plate number from the specific jurisdiction portal."""
        raise NotImplementedError("Subclasses must implement fetch_fines method.")
