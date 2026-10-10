"""Aggregator and base connectors utilizing modular regional connector modules (CABA, PBA, SINAI, Córdoba, Santa Fe)."""

import logging
from app.services.connectors.base import BaseConnector, ConnectorError
from app.services.connectors.caba import CABAConnector
from app.services.connectors.pba import PBAConnector
from app.services.connectors.sinai import SINAIConnector
from app.services.connectors.cordoba import CordobaConnector
from app.services.connectors.santa_fe import SantaFeConnector
from app.services.connectors.national_monitor import NationalMonitorConnector, MunicipalScraperConnector

logger = logging.getLogger(__name__)


class NationalFineAggregator(NationalMonitorConnector):
    """Backward-compatible alias for NationalMonitorConnector used across existing fine monitor services."""
    pass
