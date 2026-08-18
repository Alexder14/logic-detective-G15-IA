"""Estado de las investigaciones en curso: descubrimiento progresivo y bitácora.

Una investigación es una partida sobre un caso: agrupa qué evidencias y
declaraciones ya se examinaron, cuántas pistas se pidieron (con su costo en
puntaje) y el registro de acciones que exige el enunciado ("cada acción
realizada por el usuario deberá quedar registrada en una bitácora de
investigación").

Vive en memoria, sin persistencia entre reinicios del proceso: el enunciado no
pide guardar investigaciones entre sesiones del servidor, solo llevar la
bitácora mientras dura una. El candado protege el diccionario compartido
porque FastAPI puede atender pedidos concurrentes en hilos distintos -- es el
mismo patrón que el candado de `MotorProlog` en `prolog_engine.py`, pero para
este estado en vez de para la conexión con Prolog.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

#: Puntaje con el que arranca toda investigación.
PUNTAJE_INICIAL = 100

#: Cuánto descuenta pedir una pista.
COSTO_PISTA = 5

#: Tipos de acción del diagrama de flujo (ARQUITECTURA.md): consultar,
#: interrogar, analizar, deducir, pedir_ayuda y acusar.
TIPOS_ACCION = frozenset(
    {"consultar", "interrogar", "analizar", "deducir", "pedir_ayuda", "acusar"}
)


@dataclass
class AccionBitacora:
    """Una entrada de la bitácora: qué tipo de acción fue, y su detalle."""

    tipo: str
    detalle: str
    momento: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def a_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo,
            "detalle": self.detalle,
            "momento": self.momento.isoformat(),
        }


@dataclass
class Investigacion:
    """Progreso de un usuario resolviendo un caso."""

    id: str
    caso_id: str
    evidencias_examinadas: set[str] = field(default_factory=set)
    declaraciones_interrogadas: set[str] = field(default_factory=set)
    pistas_usadas: list[str] = field(default_factory=list)
    puntaje: int = PUNTAJE_INICIAL
    bitacora: list[AccionBitacora] = field(default_factory=list)

    def registrar(self, tipo: str, detalle: str) -> None:
        """Agrega una entrada a la bitácora.

        No valida `tipo` contra TIPOS_ACCION a propósito: es una lista de
        referencia para quien lee el código, no un enum cerrado que bloquee
        una acción nueva el día que el equipo agregue una.
        """
        self.bitacora.append(AccionBitacora(tipo, detalle))


class AlmacenInvestigaciones:
    """Investigaciones en memoria, indexadas por id, con acceso serializado."""

    def __init__(self) -> None:
        self._investigaciones: dict[str, Investigacion] = {}
        self._candado = threading.Lock()

    def crear(self, caso_id: str) -> Investigacion:
        investigacion = Investigacion(id=str(uuid.uuid4()), caso_id=caso_id)
        with self._candado:
            self._investigaciones[investigacion.id] = investigacion
        return investigacion

    def obtener(self, investigacion_id: str) -> Investigacion | None:
        with self._candado:
            return self._investigaciones.get(investigacion_id)


#: Instancia única que usan los endpoints, igual que `motor` en prolog_engine.py.
almacen = AlmacenInvestigaciones()
