"""Configuración compartida de las pruebas.

El motor se inicializa una sola vez por sesión: PySwip arranca una única
máquina SWI-Prolog dentro del proceso, y reinicializarla en cada prueba es
lento y frágil.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

# Permite importar `app.*` sin instalar el backend como paquete.
sys.path.insert(0, str(RAIZ / "backend"))


@pytest.fixture(scope="session")
def motor():
    """Motor de Prolog ya cargado, compartido por toda la sesión."""
    from app.prolog_engine import motor as instancia

    instancia.iniciar()
    if not instancia.disponible:
        pytest.fail(
            "No se pudo iniciar SWI-Prolog vía PySwip: "
            f"{instancia.error}. Instalá swi-prolog-nox y pyswip."
        )
    return instancia


@pytest.fixture(scope="session")
def cliente(motor):
    """Cliente HTTP contra la API, sin levantar un servidor."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def casos_cargados(motor) -> list[str]:
    """Identificadores de los casos registrados en caso_modulo/1."""
    return [fila["M"] for fila in motor.filas("caso_modulo(M)")]


@pytest.fixture(scope="session")
def interfaz():
    """Módulo de la interfaz Flask (`frontend/app.py`).

    Se carga por ruta y bajo otro nombre porque `frontend/app.py` y el paquete
    `backend/app/` competirían por el nombre `app` en sys.modules.
    """
    import importlib.util

    ruta = RAIZ / "frontend" / "app.py"
    spec = importlib.util.spec_from_file_location("interfaz_web", ruta)
    modulo = importlib.util.module_from_spec(spec)
    # Tiene que estar en sys.modules *antes* de ejecutarlo: Flask deduce de ahí
    # la carpeta de plantillas, y sin esto las busca desde el directorio actual.
    sys.modules["interfaz_web"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def navegador(interfaz):
    """Cliente HTTP contra la interfaz, sin levantar un servidor."""
    interfaz.app.config["TESTING"] = True
    with interfaz.app.test_client() as cliente_web:
        yield cliente_web
