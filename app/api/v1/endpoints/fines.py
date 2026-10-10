"""Protected B2B traffic fine monitoring API endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
import time
from app.core.security import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.fine import (
    VehicleQueryRequest,
    VehicleFinesResponse,
    FleetBatchQueryRequest,
    FleetBatchQueryResponse,
    BatchPlatesRequest,
)
from app.services.fine_monitor import FineMonitorService
from app.services.excel_service import ExcelReportService

router = APIRouter(
    prefix="/fines",
    tags=["Fine Monitoring"],
)

fine_service = FineMonitorService()

# In-memory cache with TTL (300 seconds / 5 minutes)
_fine_cache = {}

def _get_cache_key(payload: VehicleQueryRequest) -> str:
    return f"{payload.country_code}:{payload.plate_number.upper().strip()}"


@router.post(
    "/check",
    response_model=VehicleFinesResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Fines for Single Vehicle",
    description="Inspect pending or historical traffic fines for a registered fleet vehicle. Auth is fully disabled for direct Swagger UI testing.",
)
async def check_vehicle_fines(
    payload: VehicleQueryRequest,
):
    cache_key = _get_cache_key(payload)
    now = time.time()
    
    if cache_key in _fine_cache:
        cached_data, expiry_time = _fine_cache[cache_key]
        if now < expiry_time:
            return cached_data
        else:
            del _fine_cache[cache_key]
            
    result = await fine_service.query_vehicle_fines(payload)
    _fine_cache[cache_key] = (result, now + 300)
    return result


@router.post(
    "/batch",
    response_model=FleetBatchQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk Fleet Fine Monitoring",
    description="Perform automated fine monitoring across an entire enterprise fleet (bounded to max 50 items).",
)
async def batch_fleet_monitor(
    payload: FleetBatchQueryRequest,
    current_tenant: Tenant = Depends(get_current_active_tenant),
):
    return await fine_service.batch_monitor_fleet(payload)


@router.post(
    "/report/excel",
    status_code=status.HTTP_200_OK,
    summary="Download Excel Cumulative Fines Report for CABA & PBA",
    description="Receive a list of license plates and download an Excel (.xlsx) report with accumulated fine details across CABA and Provincia de Buenos Aires.",
)
async def download_fines_excel_report(
    payload: BatchPlatesRequest,
):
    reports = []
    for plate in payload.plates:
        query = VehicleQueryRequest(plate_number=plate, country_code="AR")
        res = await fine_service.query_vehicle_fines(query)
        reports.append(res)

    excel_bytes = ExcelReportService.generate_fines_excel(reports)
    
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="reporte_multas_caba_pba.xlsx"'
        },
    )


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="B2B Fine Monitoring Telemetry",
    description="Aggregate metrics and query quotas for the authenticated organization.",
)
async def get_monitoring_stats(
    current_tenant: Tenant = Depends(get_current_active_tenant),
):
    return {
        "status": "active",
        "tenant_id": current_tenant.id,
        "tenant_name": current_tenant.name,
        "monitoring_engine": "automated-registry-sync",
        "active_connectors": ["AR-DGT", "REG-MUNICIPAL"],
    }
