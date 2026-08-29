"""Utilidades que comparten los endpoints de investigación y los de administración.

Están acá y no en `main.py` porque el módulo administrativo las necesita y no
puede importarlo: es al revés, `main.py` monta su router.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from .prolog_engine import ErrorConsulta, MotorNoDisponible, motor
from .terminos import ValorInvalido
from .terminos import atomo as _atomo_validado


def consultar(meta: str) -> list[dict[str, Any]]:
    """Ejecuta una meta y traduce los fallos del motor a errores HTTP."""
    try:
        return motor.filas(meta)
    except MotorNoDisponible as exc:
        raise HTTPException(
            status_code=503, detail=f"Motor Prolog no disponible: {exc}"
        )
    except ErrorConsulta as exc:
        raise HTTPException(status_code=500, detail=f"Error en la consulta: {exc}")


def atomo(valor: str, campo: str) -> str:
    """Valida que el valor sea un átomo de Prolog antes de interpolarlo.

    Las metas se arman concatenando texto, así que sin esto un parámetro como
    `caso1), halt, foo(` se ejecutaría como código Prolog.
    """
    try:
        return _atomo_validado(valor, campo)
    except ValorInvalido as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def exigir_caso(caso_id: str) -> str:
    """Valida el identificador y da 404 si el caso no está en caso_modulo/1."""
    caso = atomo(caso_id, "caso_id")
    if not consultar(f"caso_modulo({caso})"):
        raise HTTPException(status_code=404, detail=f"El caso '{caso}' no existe")
    return caso


def casos_de_ejemplo() -> set[str]:
    """Casos de referencia, que no cuentan entre los tres entregables.

    No tienen que alcanzar los mínimos, así que `estado_caso/3` los reporta
    incompletos y la interfaz necesita saberlo para no presentarlos como trabajo
    a medio hacer.
    """
    return {fila["M"] for fila in consultar("api_caso_de_ejemplo(M)")}
