"""Main application entry point for B2B SaaS Traffic Fine Monitoring."""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from app.core.config import settings
from app.core.security import SecurityHeadersMiddleware
from app.api.v1.router import api_router

# Configure secure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
)
logger = logging.getLogger("fine_monitor_app")

# Concurrency & Rate Limiting: Maximum 100 concurrent requests/sessions
concurrency_limiter = asyncio.Semaphore(100)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager handling startup initialization and graceful shutdown."""
    logger.info(
        "Starting %s v%s in %s environment",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    yield
    logger.info("Gracefully shutting down %s", settings.APP_NAME)


# Initialize FastAPI application with security configurations
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de Monitoreo de Infracciones de Tránsito",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

# Concurrency Limiter Middleware
@app.middleware("http")
async def concurrency_limit_middleware(request: Request, call_next):
    if concurrency_limiter.locked():
        # Check if we can acquire without waiting or limit reached
        pass
    
    try:
        # Try acquiring semaphore with a short timeout or directly limit
        async with concurrency_limiter:
            response = await call_next(request)
            return response
    except Exception as exc:
        logger.warning("Concurrency limit reached or request rejected: %s", str(exc))
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "TooManyRequests",
                "message": "El sistema ha alcanzado el límite máximo de consultas simultáneas (100). Por favor, intente nuevamente en unos instantes.",
            },
        )

# 1. Defense-in-depth: Custom Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 2. Strict Cross-Origin Resource Sharing (CORS) Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


# 3. Global Exception Handler to prevent Internal Information Leakage
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception processing request %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please contact system support.",
        },
    )


# 4. Mount API routers
app.include_router(api_router, prefix="/api")


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root():
    """Modern web UI for searching fines and downloading Excel reports."""
    return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoreo de Multas CABA y PBA | SaaS B2B</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .hero-section { background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%); color: white; padding: 2.5rem 0; border-radius: 0 0 1.5rem 1.5rem; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .card { border: none; border-radius: 1rem; box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.05); }
        .table th { background-color: #e9ecef; font-weight: 600; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.5px; }
        .badge-caba { background-color: #fd7e14; color: white; }
        .badge-pba { background-color: #20c997; color: white; }
        .badge-other { background-color: #6c757d; color: white; }
        .status-pending { color: #dc3545; font-weight: 600; }
        .status-paid { color: #198754; font-weight: 600; }
        .spinner-border { width: 3rem; height: 3rem; }
    </style>
</head>
<body>

    <div class="hero-section text-center">
        <div class="container">
            <h1 class="display-5 fw-bold mb-2"><i class="fas fa-shield-alt me-2"></i>Monitoreo Inteligente de Multas</h1>
            <p class="lead mb-0">Consulta en tiempo real de infracciones viales en CABA y Provincia de Buenos Aires</p>
        </div>
    </div>

    <div class="container mb-5">
        <!-- Search & Excel Export Controls -->
        <div class="row justify-content-center mb-4">
            <div class="col-lg-10">
                <div class="card p-4">
                    <form id="searchForm" class="row g-3 align-items-center">
                        <div class="col-md-7">
                            <label for="plateInput" class="form-label fw-semibold text-secondary">Dominio / Patente del Vehículo</label>
                            <div class="input-group input-group-lg">
                                <span class="input-group-text bg-white"><i class="fas fa-car text-primary"></i></span>
                                <input type="text" class="form-control" id="plateInput" placeholder="Ej. AA123BB o AB123CD" required style="text-transform: uppercase;">
                            </div>
                        </div>
                        <div class="col-md-5 d-flex align-items-end gap-2 mt-3 mt-md-0">
                            <button type="submit" class="btn btn-primary btn-lg flex-grow-1 shadow-sm">
                                <i class="fas fa-search me-2"></i>Buscar Multas
                            </button>
                            <button type="button" id="excelBtn" class="btn btn-success btn-lg shadow-sm" title="Descargar Reporte Excel">
                                <i class="fas fa-file-excel me-2"></i>Excel
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <!-- Summary & Results Section -->
        <div class="row justify-content-center" id="resultsContainer" style="display: none;">
            <div class="col-lg-10">
                <!-- Summary Card -->
                <div class="card mb-4 bg-white border-start border-primary border-4 shadow-sm">
                    <div class="card-body d-flex justify-content-between align-items-center flex-wrap gap-3">
                        <div>
                            <h5 class="card-title text-muted mb-1">Vehículo Consultado</h5>
                            <h3 class="fw-bold text-dark mb-0" id="resPlate">-</h3>
                        </div>
                        <div>
                            <h5 class="card-title text-muted mb-1">Total Infracciones</h5>
                            <h3 class="fw-bold text-primary mb-0" id="resTotalCount">0</h3>
                        </div>
                        <div>
                            <h5 class="card-title text-muted mb-1">Deuda Acumulada</h5>
                            <h3 class="fw-bold text-danger mb-0" id="resTotalAmount">$0.00</h3>
                        </div>
                    </div>
                </div>

                <!-- Fines Table Card -->
                <div class="card shadow-sm">
                    <div class="card-header bg-white py-3">
                        <h5 class="mb-0 fw-bold text-dark"><i class="fas fa-list-alt me-2 text-primary"></i>Detalle de Infracciones (CABA & PBA)</h5>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-hover align-middle mb-0">
                                <thead>
                                    <tr>
                                        <th class="ps-4">Jurisdicción</th>
                                        <th>ID / Acta</th>
                                        <th>Infracción</th>
                                        <th>Fecha</th>
                                        <th>Monto</th>
                                        <th class="text-center">Estado</th>
                                        <th class="pe-4">Descripción</th>
                                    </tr>
                                </thead>
                                <tbody id="finesTableBody">
                                    <!-- Dynamic rows injected here -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Loading Spinner -->
        <div id="loadingSpinner" class="text-center py-5" style="display: none;">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Buscando...</span>
            </div>
            <p class="text-muted mt-3 fw-semibold">Consultando bases de datos de CABA y Provincia de Buenos Aires...</p>
        </div>

        <!-- Empty State / Initial Alert -->
        <div class="row justify-content-center" id="initialState">
            <div class="col-lg-10 text-center py-5">
                <div class="text-muted opacity-75">
                    <i class="fas fa-search fa-3x mb-3"></i>
                    <h4>Ingrese una patente para comenzar la auditoría de multas</h4>
                    <p class="text-secondary">El sistema consultará de manera unificada los registros oficiales.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="text-center py-4 text-muted border-top bg-white">
        <div class="container">
            <small>&copy; 2026 Fleet Traffic Fine Monitor SaaS &bull; CABA & PBA Integration Engine</small>
        </div>
    </footer>

    <!-- Bootstrap JS Bundle -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const searchForm = document.getElementById('searchForm');
        const plateInput = document.getElementById('plateInput');
        const loadingSpinner = document.getElementById('loadingSpinner');
        const resultsContainer = document.getElementById('resultsContainer');
        const initialState = document.getElementById('initialState');
        const finesTableBody = document.getElementById('finesTableBody');
        const resPlate = document.getElementById('resPlate');
        const resTotalCount = document.getElementById('resTotalCount');
        const resTotalAmount = document.getElementById('resTotalAmount');
        const excelBtn = document.getElementById('excelBtn');

        let lastSearchedPlate = '';

        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const plate = plateInput.value.trim().toUpperCase();
            if (!plate) return;

            lastSearchedPlate = plate;
            initialState.style.display = 'none';
            resultsContainer.style.display = 'none';
            loadingSpinner.style.display = 'block';

            try {
                const response = await fetch('/api/v1/fines/check', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plate_number: plate, country_code: 'AR' })
                });

                if (!response.ok) {
                    throw new Error('Error al consultar las multas del vehículo.');
                }

                const data = await response.json();
                renderResults(data);
            } catch (err) {
                alert('Ocurrió un error al procesar la solicitud: ' + err.message);
            } finally {
                loadingSpinner.style.display = 'none';
            }
        });

        function renderResults(data) {
            resPlate.textContent = data.plate_number;
            resTotalCount.textContent = data.total_fines;
            resTotalAmount.textContent = new Intl.NumberFormat('es-AR', { style: 'currency', currency: data.currency || 'ARS' }).format(data.total_amount);

            finesTableBody.innerHTML = '';

            if (data.fines.length === 0) {
                finesTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No se registran multas pendientes para el dominio ${data.plate_number}.</td></tr>`;
            } else {
                data.fines.forEach(fine => {
                    let badgeClass = 'badge-other';
                    let auth = fine.authority || 'Desconocida';
                    if (auth.toLowerCase().includes('caba') || auth.toLowerCase().includes('buenos aires ciudad')) {
                        badgeClass = 'badge-caba';
                        auth = 'CABA';
                    } else if (auth.toLowerCase().includes('provincia') || auth.toLowerCase().includes('pba')) {
                        badgeClass = 'badge-pba';
                        auth = 'Provincia de Bs. As.';
                    }

                    const statusClass = fine.status === 'PENDING' ? 'status-pending' : 'status-paid';
                    const statusText = fine.status === 'PENDING' ? 'Pendiente' : 'Pagada';
                    const dateFormatted = new Date(fine.issue_date).toLocaleDateString('es-AR');
                    const amountFormatted = new Intl.NumberFormat('es-AR', { style: 'currency', currency: fine.currency || 'ARS' }).format(fine.amount);

                    const row = `
                        <tr>
                            <td class="ps-4"><span class="badge ${badgeClass} px-2 py-1">${auth}</span></td>
                            <td class="fw-semibold font-monospace">${fine.fine_id}</td>
                            <td>${fine.infraction_code}</td>
                            <td>${dateFormatted}</td>
                            <td class="fw-bold text-danger">${amountFormatted}</td>
                            <td class="text-center"><span class="${statusClass}">${statusText}</span></td>
                            <td class="pe-4 text-muted small">${fine.description || '-'}</td>
                        </tr>
                    `;
                    finesTableBody.innerHTML += row;
                });
            }

            resultsContainer.style.display = 'block';
        }

        excelBtn.addEventListener('click', async () => {
            const plate = lastSearchedPlate || plateInput.value.trim().toUpperCase();
            if (!plate) {
                alert('Por favor, ingrese o busque una patente primero para descargar el reporte.');
                plateInput.focus();
                return;
            }

            try {
                excelBtn.disabled = true;
                excelBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generando...';

                const response = await fetch('/api/v1/fines/report/excel', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plates: [plate] })
                });

                if (!response.ok) {
                    throw new Error('Error al generar el archivo Excel.');
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `reporte_multas_${plate}.xlsx`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } catch (err) {
                alert('Error al descargar el reporte Excel: ' + err.message);
            } finally {
                excelBtn.disabled = false;
                excelBtn.innerHTML = '<i class="fas fa-file-excel me-2"></i>Excel';
            }
        });
    </script>
</body>
</html>
    """



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        server_header=False,
    )
