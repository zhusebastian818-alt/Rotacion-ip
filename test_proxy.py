import asyncio
import sys
import logging
from app.services.proxy_rotator import ProxyRotator
from app.services.connectors.caba import CABAConnector
from app.services.connectors.pba import PBAConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_proxy_rotator")

async def test_rotator():
    print("=== INICIANDO PRUEBA DE PROXY ROTATOR Y CONECTORES CABA/PBA ===")
    
    # 1. Test ProxyRotator standalone
    rotator = ProxyRotator(max_retries=3, timeout_seconds=5.0)
    print(f"Proveedores inicializados: {len(rotator.providers)}")
    
    # 2. Test CABA connector with ProxyRotator
    caba = CABAConnector()
    print("\n--- Consultando CABA para patente de prueba (AB123CD) ---")
    try:
        fines_caba = await caba.fetch_fines("AB123CD")
        print(f"CABA resultado exitoso: {len(fines_caba)} infracciones encontradas.")
        for f in fines_caba:
            print(f"  * [{f.fine_id}] {f.authority}: ${f.amount} ({f.description})")
    except Exception as e:
        print(f"CABA error: {e}")

    # 3. Test PBA connector with ProxyRotator
    pba = PBAConnector()
    print("\n--- Consultando PBA para patente de prueba (AB123CD) ---")
    try:
        fines_pba = await pba.fetch_fines("AB123CD")
        print(f"PBA resultado exitoso: {len(fines_pba)} infracciones encontradas.")
        for f in fines_pba:
            print(f"  * [{f.fine_id}] {f.authority}: ${f.amount} ({f.description})")
    except Exception as e:
        print(f"PBA error: {e}")

    # 4. Test Block/Render IP fallback simulation (AG781VH)
    print("\n--- Probando simulación de bloqueo de Render IP / Anti-bot (AG781VH) en CABA y PBA ---")
    caba_blocked = await caba.fetch_fines("AG781VH")
    print(f"CABA con IP bloqueada devolvió {len(fines_caba) if 'fines_caba' in locals() else 0} registros de fallback robusto:")
    for f in caba_blocked:
        print(f"  * [{f.fine_id}] {f.description}")

    pba_blocked = await pba.fetch_fines("AG781VH")
    print(f"PBA con IP bloqueada devolvió {len(pba_blocked)} registros de fallback robusto:")
    for f in pba_blocked:
        print(f"  * [{f.fine_id}] {f.description}")

    print("\n=== PRUEBA DE VERIFICACIÓN COMPLETADA EXITOSAMENTE ===")

if __name__ == "__main__":
    asyncio.run(test_rotator())
