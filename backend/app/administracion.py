"""Persistencia del módulo administrativo.

Los hechos de los casos viven en archivos `.pl` escritos a mano, con sus reglas
al lado; editarlos desde la interfaz sería reescribir código fuente. En vez de
eso se lleva una bitácora de cambios: el motor arranca siempre desde los `.pl`
de fábrica y encima se aplican las operaciones del administrador (`assertz` las
altas, `retractall` las bajas), que el motor acepta en caliente porque
reglas_base.pl declara `dynamic` el esquema.

La bitácora se guarda en JSON y se reaplica al arrancar, así que los cambios
sobreviven a un reinicio. Como cada baja guarda el texto de lo que borró,
también se puede recorrer al revés: eso es restaurar valores de fábrica.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .prolog_engine import MotorProlog, motor
from .terminos import texto

#: Raíz del repositorio, igual que en prolog_engine.py.
RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

#: En Docker va montado como volumen: es el único estado que el contenedor no
#: puede reconstruir solo.
DIRECTORIO_DATOS = Path(os.environ.get("LD_DATOS", RAIZ_PROYECTO / "datos")).resolve()

#: Ruta absoluta porque los casos generados no quedan junto a los de fábrica.
REGLAS_BASE = (RAIZ_PROYECTO / "prolog" / "reglas_base.pl").as_posix()

#: Versión del formato, para poder migrar el archivo en vez de descartarlo.
VERSION_FORMATO = 1


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Operacion:
    """Un cambio aplicado a la base de conocimiento.

    En un alta, `termino` es el hecho que se afirma. En una baja es el patrón
    que se retira, con comodines, y `removidos` guarda lo que ese patrón se
    llevó: es lo que permite deshacerla.
    """

    modulo: str
    tipo: str
    termino: str
    removidos: list[str] = field(default_factory=list)
    momento: str = field(default_factory=_ahora)

    def a_dict(self) -> dict[str, Any]:
        return {
            "modulo": self.modulo,
            "tipo": self.tipo,
            "termino": self.termino,
            "removidos": self.removidos,
            "momento": self.momento,
        }

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> "Operacion":
        return cls(
            modulo=datos["modulo"],
            tipo=datos["tipo"],
            termino=datos["termino"],
            removidos=list(datos.get("removidos", [])),
            momento=datos.get("momento", _ahora()),
        )


@dataclass
class CasoCreado:
    """Un caso dado de alta desde administración."""

    modulo: str
    titulo: str
    descripcion: str
    dificultad: str

    def a_dict(self) -> dict[str, Any]:
        return {
            "modulo": self.modulo,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "dificultad": self.dificultad,
        }


class ErrorAdministracion(RuntimeError):
    """Una operación administrativa no se pudo completar."""


class AlmacenAdministracion:
    """Bitácora de cambios administrativos, persistida en JSON.

    El candado serializa las escrituras: FastAPI puede atender pedidos
    concurrentes, y acá se comparten una lista y un archivo.
    """

    def __init__(
        self,
        directorio: Path = DIRECTORIO_DATOS,
        motor_prolog: MotorProlog | None = None,
    ) -> None:
        self.directorio = directorio
        self.archivo = directorio / "administracion.json"
        self.directorio_casos = directorio / "casos"
        self.motor = motor_prolog if motor_prolog is not None else motor
        self._candado = threading.RLock()
        self._operaciones: list[Operacion] = []
        self._casos_creados: dict[str, CasoCreado] = {}
        self._casos_eliminados: list[str] = []

    # -- persistencia --------------------------------------------------------

    def leer(self) -> None:
        """Carga la bitácora del disco. No toca el motor."""
        with self._candado:
            self._operaciones = []
            self._casos_creados = {}
            self._casos_eliminados = []
            if not self.archivo.is_file():
                return
            try:
                datos = json.loads(self.archivo.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise ErrorAdministracion(
                    f"No se pudo leer {self.archivo}: {exc}"
                ) from exc
            self._operaciones = [
                Operacion.desde_dict(fila) for fila in datos.get("operaciones", [])
            ]
            self._casos_creados = {
                fila["modulo"]: CasoCreado(**fila)
                for fila in datos.get("casos_creados", [])
            }
            self._casos_eliminados = list(datos.get("casos_eliminados", []))

    def _escribir(self) -> None:
        """Guarda la bitácora, con el candado ya tomado.

        Escribe a un temporal y lo mueve encima: si el proceso muere a mitad,
        en el disco queda la versión anterior completa y no un JSON truncado.
        """
        self.directorio.mkdir(parents=True, exist_ok=True)
        datos = {
            "version": VERSION_FORMATO,
            "actualizado": _ahora(),
            "casos_creados": [caso.a_dict() for caso in self._casos_creados.values()],
            "casos_eliminados": self._casos_eliminados,
            "operaciones": [operacion.a_dict() for operacion in self._operaciones],
        }
        temporal = self.archivo.with_suffix(".json.tmp")
        temporal.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporal, self.archivo)

    # -- arranque ------------------------------------------------------------

    def aplicar_al_motor(self) -> None:
        """Reaplica el estado guardado sobre el motor recién cargado.

        Es lo que hace que los cambios persistan. Se llama una vez, al arrancar.
        """
        with self._candado:
            self.leer()
            for caso in self._casos_creados.values():
                self._montar_modulo(caso)
            for modulo in self._casos_eliminados:
                self.motor.ejecutar(f"olvidar_caso({modulo})")
            for operacion in self._operaciones:
                self._ejecutar(operacion)

    def _ejecutar(self, operacion: Operacion) -> None:
        """Aplica una operación al motor."""
        if operacion.tipo == "alta":
            self.motor.afirmar(operacion.modulo, operacion.termino)
        else:
            self.motor.retirar(operacion.modulo, operacion.termino)

    def _montar_modulo(self, caso: CasoCreado) -> None:
        """Genera y consulta el módulo de Prolog de un caso creado acá.

        El `include` de reglas_base.pl es lo que le da las reglas de inferencia
        y el esquema dinámico. El resto de sus hechos entra por la bitácora.
        """
        self.directorio_casos.mkdir(parents=True, exist_ok=True)
        archivo = self.directorio_casos / f"{caso.modulo}.pl"
        archivo.write_text(
            "% Caso generado por el módulo administrativo de Logic Detective.\n"
            "% No se edita a mano: se regenera al arrancar desde\n"
            f"% {self.archivo}\n\n"
            f":- module({caso.modulo}, []).\n\n"
            f":- include('{REGLAS_BASE}').\n\n"
            "caso({id}, {titulo}, {descripcion}, {dificultad}).\n".format(
                id=caso.modulo,
                titulo=texto(caso.titulo, "titulo"),
                descripcion=texto(caso.descripcion, "descripcion"),
                dificultad=caso.dificultad,
            ),
            encoding="utf-8",
        )
        self.motor.cargar(archivo)
        self.motor.ejecutar(f"registrar_caso({caso.modulo})")

    # -- operaciones sobre hechos -------------------------------------------

    def alta(self, modulo: str, termino: str) -> None:
        """Afirma un hecho y lo anota en la bitácora."""
        with self._candado:
            operacion = Operacion(modulo=modulo, tipo="alta", termino=termino)
            self._ejecutar(operacion)
            self._operaciones.append(operacion)
            self._escribir()

    def baja(self, modulo: str, patron: str) -> int:
        """Retira los hechos que unifican con el patrón. Devuelve cuántos borró.

        Guarda el texto de cada uno antes de tocarlo: sin eso la eliminación no
        se podría deshacer.
        """
        with self._candado:
            removidos = self._hechos(modulo, patron)
            if not removidos:
                return 0
            operacion = Operacion(
                modulo=modulo, tipo="baja", termino=patron, removidos=removidos
            )
            self._ejecutar(operacion)
            self._operaciones.append(operacion)
            self._escribir()
            return len(removidos)

    def reemplazar(self, modulo: str, patron: str, termino: str) -> None:
        """Modifica un hecho: lo retira por su clave y afirma el nuevo."""
        with self._candado:
            self.baja(modulo, patron)
            self.alta(modulo, termino)

    def _hechos(self, modulo: str, patron: str) -> list[str]:
        """Texto de los hechos del módulo que unifican con el patrón."""
        filas = self.motor.filas(f"api_admin_hechos({modulo}, ({patron}), Texto)")
        return [fila["Texto"] for fila in filas]

    def existe_hecho(self, modulo: str, patron: str) -> bool:
        """True si el caso ya tiene un hecho que unifica con el patrón."""
        return bool(self._hechos(modulo, patron))

    # -- operaciones sobre casos --------------------------------------------

    def crear_caso(
        self, modulo: str, titulo: str, descripcion: str, dificultad: str
    ) -> None:
        """Da de alta un caso nuevo con su módulo de Prolog."""
        with self._candado:
            caso = CasoCreado(
                modulo=modulo,
                titulo=titulo,
                descripcion=descripcion,
                dificultad=dificultad,
            )
            self._montar_modulo(caso)
            self._casos_creados[modulo] = caso
            if modulo in self._casos_eliminados:
                self._casos_eliminados.remove(modulo)
            self._escribir()

    def modificar_caso(
        self, modulo: str, titulo: str, descripcion: str, dificultad: str
    ) -> None:
        """Cambia la ficha de un caso: el hecho `caso/4`.

        En uno creado acá se actualiza además el `.pl` generado, para que el
        archivo no contradiga a la bitácora.
        """
        with self._candado:
            self.reemplazar(
                modulo,
                f"caso({modulo},_,_,_)",
                "caso({id},{titulo},{descripcion},{dificultad})".format(
                    id=modulo,
                    titulo=texto(titulo, "titulo"),
                    descripcion=texto(descripcion, "descripcion"),
                    dificultad=dificultad,
                ),
            )
            if modulo in self._casos_creados:
                caso = self._casos_creados[modulo]
                caso.titulo = titulo
                caso.descripcion = descripcion
                caso.dificultad = dificultad
                self._escribir()

    def eliminar_caso(self, modulo: str) -> None:
        """Saca un caso del catálogo.

        Uno de fábrica solo se oculta: sus hechos siguen intactos y restaurar lo
        devuelve entero. Uno creado acá se borra de verdad, porque no hay estado
        de fábrica al que volver.
        """
        with self._candado:
            self.motor.ejecutar(f"olvidar_caso({modulo})")
            if modulo in self._casos_creados:
                self.motor.ejecutar(f"vaciar_caso({modulo})")
                del self._casos_creados[modulo]
                self._operaciones = [
                    operacion
                    for operacion in self._operaciones
                    if operacion.modulo != modulo
                ]
                archivo = self.directorio_casos / f"{modulo}.pl"
                archivo.unlink(missing_ok=True)
            elif modulo not in self._casos_eliminados:
                self._casos_eliminados.append(modulo)
            self._escribir()

    # -- vuelta atrás --------------------------------------------------------

    def restaurar(self) -> int:
        """Deshace todos los cambios administrativos. Devuelve cuántos deshizo.

        Recorre la bitácora al revés aplicando el inverso de cada operación: un
        alta se retira, y una baja se repone afirmando lo que había guardado.
        """
        with self._candado:
            deshechas = 0
            for operacion in reversed(self._operaciones):
                if operacion.tipo == "alta":
                    self.motor.retirar(operacion.modulo, operacion.termino)
                else:
                    for hecho_texto in operacion.removidos:
                        self.motor.afirmar(operacion.modulo, hecho_texto)
                deshechas += 1
            self._operaciones = []

            for modulo in self._casos_eliminados:
                self.motor.ejecutar(f"registrar_caso({modulo})")
            self._casos_eliminados = []

            for modulo in list(self._casos_creados):
                self.motor.ejecutar(f"vaciar_caso({modulo})")
                self.motor.ejecutar(f"olvidar_caso({modulo})")
                (self.directorio_casos / f"{modulo}.pl").unlink(missing_ok=True)
            self._casos_creados = {}

            self._escribir()
            return deshechas

    # -- lectura -------------------------------------------------------------

    @property
    def cambios(self) -> int:
        with self._candado:
            return len(self._operaciones)

    def historial(self, limite: int = 50) -> list[dict[str, Any]]:
        """Las últimas operaciones, de la más reciente a la más vieja."""
        with self._candado:
            return [
                operacion.a_dict()
                for operacion in reversed(self._operaciones[-limite:])
            ]

    def casos_creados(self) -> list[str]:
        with self._candado:
            return sorted(self._casos_creados)

    def casos_eliminados(self) -> list[str]:
        with self._candado:
            return list(self._casos_eliminados)


#: Instancia única que usan los endpoints.
administracion = AlmacenAdministracion()
