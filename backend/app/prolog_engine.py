"""Integración con SWI-Prolog vía PySwip.

Es la única parte del backend que habla con el motor; el resto usa
`motor.filas(...)`.

Dos cosas que hay que respetar al tocar este archivo:

1. Un solo hilo. SWI-Prolog no es seguro para llamadas concurrentes desde
   varios hilos de Python. Los endpoints de `main.py` son `async def` para que
   todas las consultas caigan en el hilo del bucle de eventos; el candado de
   abajo es la segunda red.

2. Valores planos. PySwip 0.3.x no traduce bien los términos anidados: una
   lista de átomos dentro de un término llega como `Atom('764549')`. Los
   predicados `api_*` de `logic_detective.pl` devuelven una fila por solución
   con argumentos atómicos. Si te falta un dato, agregá un `api_*` plano en
   Prolog en vez de desarmar términos acá.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

# Si PySwip o libswipl no están disponibles, la API debe levantar igual y
# reportarlo en /health en vez de morir al arrancar: así se puede diagnosticar
# el contenedor.
try:
    from pyswip import Prolog

    ERROR_IMPORT: str | None = None
except Exception as exc:  # pragma: no cover - depende del entorno
    Prolog = None  # type: ignore[assignment]
    ERROR_IMPORT = f"{type(exc).__name__}: {exc}"


# Punto de entrada del motor: logic_detective.pl carga reglas_base.pl y los casos.
RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
ARCHIVO_ENTRADA = RAIZ_PROYECTO / "prolog" / "logic_detective.pl"


def _a_python(valor: Any) -> Any:
    """Normaliza un valor devuelto por PySwip.

    Los átomos llegan como str, los enteros como int y las cadenas de Prolog
    como bytes.
    """
    if isinstance(valor, bytes):
        return valor.decode("utf-8", errors="replace")
    if isinstance(valor, list):
        return [_a_python(elemento) for elemento in valor]
    if isinstance(valor, (int, float, str)) or valor is None:
        return valor
    return str(valor)


class MotorProlog:
    """Envoltorio de una instancia de SWI-Prolog."""

    def __init__(self, archivo: Path = ARCHIVO_ENTRADA) -> None:
        self.archivo = archivo
        self._prolog: Any = None
        self._candado = threading.Lock()
        self.error: str | None = ERROR_IMPORT

    # -- ciclo de vida -------------------------------------------------------

    def iniciar(self) -> None:
        """Carga la base de conocimiento. Se llama una vez al arrancar la API."""
        if Prolog is None:
            self.error = ERROR_IMPORT or "PySwip no está instalado"
            return
        if not self.archivo.is_file():
            self.error = f"No se encontró {self.archivo}"
            return
        try:
            self._prolog = Prolog()
            # consult() necesita la ruta con / incluso en Windows.
            self._prolog.consult(self.archivo.as_posix())
            self.error = None
        except Exception as exc:  # pragma: no cover - depende del entorno
            self._prolog = None
            self.error = f"{type(exc).__name__}: {exc}"

    @property
    def disponible(self) -> bool:
        return self._prolog is not None and self.error is None

    # -- consultas -----------------------------------------------------------

    def filas(self, meta: str, limite: int | None = None) -> list[dict[str, Any]]:
        """Ejecuta una meta y devuelve una lista de diccionarios variable -> valor.

        Devuelve `[]` si la meta falla, que en Prolog es una respuesta válida:
        por ejemplo un caso todavía sin hechos.
        """
        if not self.disponible:
            raise MotorNoDisponible(self.error or "motor no inicializado")
        with self._candado:
            try:
                soluciones = self._prolog.query(meta, maxresult=limite or -1)
                return [
                    {clave: _a_python(valor) for clave, valor in solucion.items()}
                    for solucion in soluciones
                ]
            except Exception as exc:
                raise ErrorConsulta(f"{meta} -> {type(exc).__name__}: {exc}") from exc

    def existe(self, meta: str) -> bool:
        """True si la meta tiene al menos una solución."""
        return bool(self.filas(meta, limite=1))

    # -- escritura -----------------------------------------------------------
    #
    # Las usa el módulo administrativo. Funcionan porque reglas_base.pl declara
    # `dynamic` el esquema de hechos y cada caso la incluye antes de los suyos,
    # así que el motor acepta assertz/retract con el caso ya cargado.

    def ejecutar(self, meta: str) -> bool:
        """Ejecuta una meta por su efecto y devuelve si tuvo éxito.

        `filas()` no sirve: una meta sin variables que tiene éxito devuelve una
        solución vacía, indistinguible de la lista vacía de una que falla.
        """
        if not self.disponible:
            raise MotorNoDisponible(self.error or "motor no inicializado")
        with self._candado:
            try:
                soluciones = list(self._prolog.query(f"once(({meta}))", maxresult=1))
                return bool(soluciones)
            except Exception as exc:
                raise ErrorConsulta(f"{meta} -> {type(exc).__name__}: {exc}") from exc

    def afirmar(self, modulo: str, termino: str) -> None:
        """Agrega un hecho al caso indicado."""
        self.ejecutar(f"assertz({modulo}:({termino}))")

    def retirar(self, modulo: str, patron: str) -> None:
        """Borra del caso todos los hechos que unifican con el patrón.

        retractall/1 y no retract/1: no falla si el hecho ya no está, y por eso
        reaplicar la bitácora es idempotente.
        """
        self.ejecutar(f"retractall({modulo}:({patron}))")

    def cargar(self, archivo: Path) -> None:
        """Consulta un archivo adicional: los casos creados desde administración."""
        if not self.disponible:
            raise MotorNoDisponible(self.error or "motor no inicializado")
        with self._candado:
            try:
                self._prolog.consult(archivo.as_posix())
            except Exception as exc:
                raise ErrorConsulta(
                    f"consult({archivo}) -> {type(exc).__name__}: {exc}"
                ) from exc

    def version(self) -> str | None:
        filas = self.filas("version_motor(V)", limite=1)
        return filas[0]["V"] if filas else None


class MotorNoDisponible(RuntimeError):
    """No se pudo inicializar SWI-Prolog."""


class ErrorConsulta(RuntimeError):
    """La consulta a Prolog lanzó una excepción."""


# Instancia única que usan los endpoints.
motor = MotorProlog()
