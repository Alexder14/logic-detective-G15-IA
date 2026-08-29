"""Construcción y validación de términos de Prolog.

Escribir en Prolog es armar texto que el motor va a leer como código, así que
un nombre como `sala), halt, foo(` convertiría un alta en una inyección. Acá
está la única forma de construir un término: cada valor se valida contra el
esquema de reglas_base.pl y se devuelve ya escrito.
"""

from __future__ import annotations

import re
from typing import Iterable

#: Un átomo de Prolog sin comillas.
ATOMO = re.compile(r"^[a-z][a-zA-Z0-9_]{0,63}$")

LARGO_TEXTO = 500


# El vocabulario que documenta la cabecera de reglas_base.pl. Está acá y no en
# Prolog porque quien lo necesita es la validación: el motor no rechaza un
# motivo inventado, simplemente no deduce nada con él.

DIFICULTADES = ("facil", "media", "dificil")

ROLES = ("sospechoso", "testigo", "victima")

TIPOS_RELACION = (
    "socio",
    "hermano",
    "ex_pareja",
    "jefe",
    "empleado",
    "deudor",
    "acreedor",
    "rival",
    "heredero",
    "vecino",
    "amigo",
)

TIPOS_MOTIVO = (
    "deuda",
    "herencia",
    "venganza",
    "celos",
    "despido",
    "encubrimiento",
    "dinero",
)

MEDIOS = (
    "llave",
    "codigo_alarma",
    "fuerza",
    "conocimiento_tecnico",
    "vehiculo",
    "veneno",
    "herramienta",
)

TIPOS_EVIDENCIA = (
    "huella",
    "adn",
    "video",
    "documento",
    "objeto",
    "registro",
    "testimonio",
)

#: Los hechos con los que reglas_base.pl deduce oportunidad y capacidad, con lo
#: que necesitan el formulario y la validación: si llevan hora y qué es su
#: segundo argumento.
TIPOS_OPORTUNIDAD = {
    "visto_en": {"objeto": "lugar", "hora": True},
    "registro_acceso": {"objeto": "lugar", "hora": True},
    "tiene_llave": {"objeto": "lugar", "hora": False},
    "autorizado_en": {"objeto": "lugar", "hora": False},
    "posee_medio": {"objeto": "medio", "hora": False},
}

#: Lista cerrada: las reglas de contradicción detectan los choques por
#: unificación sobre estos términos, así que una declaración con otro funtor no
#: contradiría nunca nada.
TIPOS_DECLARACION = {
    "estuvo_en": ("persona", "lugar", "hora"),
    "no_estuvo_en": ("persona", "lugar", "hora"),
    "vio_a": ("persona", "lugar", "hora"),
    "conoce_a": ("persona", "persona"),
    "no_conoce_a": ("persona", "persona"),
    "posee": ("persona", "medio"),
}

#: Respaldos de una coartada, con el tipo de su argumento. `ninguno` no lleva.
TIPOS_RESPALDO = {
    "testigo": "persona",
    "camara": "lugar",
    "documento": "evidencia",
    "ninguno": None,
}


class ValorInvalido(ValueError):
    """Un valor no cumple el esquema. Lleva el campo para poder señalarlo."""

    def __init__(self, campo: str, detalle: str) -> None:
        self.campo = campo
        self.detalle = detalle
        super().__init__(f"{campo}: {detalle}")


def atomo(valor: object, campo: str) -> str:
    """Valida un identificador y lo devuelve como átomo sin comillas."""
    if not isinstance(valor, str):
        raise ValorInvalido(campo, "se esperaba un identificador")
    limpio = valor.strip()
    if not limpio:
        raise ValorInvalido(campo, "es obligatorio")
    if not ATOMO.match(limpio):
        raise ValorInvalido(
            campo,
            "debe empezar con minúscula y contener solo letras, dígitos y guion "
            f"bajo (recibido: {valor!r})",
        )
    return limpio


def texto(valor: object, campo: str, largo: int = LARGO_TEXTO) -> str:
    """Devuelve el valor como átomo citado, listo para interpolar.

    Duplica la comilla simple y escapa la barra invertida igual que como escribe
    SWI-Prolog sus propios átomos: lo que sale de acá se vuelve a leer idéntico,
    y de eso depende poder deshacer una baja.
    """
    if not isinstance(valor, str):
        raise ValorInvalido(campo, "se esperaba texto")
    limpio = " ".join(valor.split())
    if not limpio:
        raise ValorInvalido(campo, "es obligatorio")
    if len(limpio) > largo:
        raise ValorInvalido(campo, f"no puede pasar de {largo} caracteres")
    escapado = limpio.replace("\\", "\\\\").replace("'", "''")
    return f"'{escapado}'"


def uno_de(valor: object, campo: str, opciones: Iterable[str]) -> str:
    """Valida que el valor esté en el vocabulario del esquema."""
    validas = tuple(opciones)
    if not isinstance(valor, str) or valor.strip() not in validas:
        raise ValorInvalido(
            campo, f"debe ser uno de: {', '.join(validas)} (recibido: {valor!r})"
        )
    return valor.strip()


def hora(valor: object, campo: str, permite_desconocida: bool = False) -> str:
    """Valida una hora del día: entero 0..23, o `desconocida` donde se admite."""
    if (
        permite_desconocida
        and isinstance(valor, str)
        and valor.strip() == "desconocida"
    ):
        return "desconocida"
    try:
        entero = int(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        extra = " o 'desconocida'" if permite_desconocida else ""
        raise ValorInvalido(campo, f"debe ser un entero entre 0 y 23{extra}")
    if not 0 <= entero <= 23:
        raise ValorInvalido(campo, f"debe estar entre 0 y 23 (recibido: {entero})")
    return str(entero)


def hecho(nombre: str, *argumentos: str) -> str:
    """Arma un término a partir de argumentos ya validados."""
    if not argumentos:
        return nombre
    return f"{nombre}({','.join(argumentos)})"


def patron(nombre: str, *argumentos: str) -> str:
    """Igual que `hecho`, para los términos que llevan comodines."""
    return hecho(nombre, *argumentos)


LIBRE = "_"
