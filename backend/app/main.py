"""API de Logic Detective.

Cada endpoint consulta Prolog a través de PySwip. Lo que falta es enriquecer
las respuestas, marcado con TODO(backend).

Acá no se decide nada: si hace falta una conclusión nueva se agrega un
predicado api_* plano en prolog/logic_detective.pl y este archivo solo recoge
las filas.

Documentación interactiva: http://localhost:8000/docs
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .prolog_engine import ErrorConsulta, MotorNoDisponible, motor


# --------------------------------------------------------------------------
# Aplicación
# --------------------------------------------------------------------------


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Carga la base de conocimiento una sola vez, al arrancar."""
    motor.iniciar()
    yield


app = FastAPI(
    title="Logic Detective API",
    description="Sistema experto de investigación. Motor de inferencia en Prolog.",
    version="0.1.0-esqueleto",
    lifespan=ciclo_de_vida,
)

# El frontend corre en otro puerto/contenedor. En producción conviene
# restringir esta lista al dominio real del despliegue.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Utilidades
#
# Los endpoints son `async def` para que todas las llamadas a Prolog caigan en
# el hilo del bucle de eventos. Ver la nota en prolog_engine.py.
# --------------------------------------------------------------------------


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


#: Un átomo de Prolog sin comillas: minúscula inicial, letras, dígitos y _.
ATOMO = re.compile(r"^[a-z][a-zA-Z0-9_]{0,63}$")


def atomo(valor: str, campo: str) -> str:
    """Valida que el valor sea un átomo de Prolog antes de interpolarlo.

    Las metas se arman concatenando texto, así que sin esto un parámetro como
    `caso1), halt, foo(` se ejecutaría como código Prolog. Todo lo que venga
    del cliente y termine dentro de una meta pasa por acá.
    """
    if not ATOMO.match(valor):
        raise HTTPException(
            status_code=400,
            detail=f"'{campo}' debe ser un identificador válido (recibido: {valor!r})",
        )
    return valor


def exigir_caso(caso_id: str) -> str:
    """Valida el identificador y da 404 si el caso no está en caso_modulo/1."""
    caso = atomo(caso_id, "caso_id")
    if not consultar(f"caso_modulo({caso})"):
        raise HTTPException(status_code=404, detail=f"El caso '{caso}' no existe")
    return caso


class Acusacion(BaseModel):
    """Cuerpo de POST /api/casos/{caso_id}/acusacion."""

    sospechoso: str


# --------------------------------------------------------------------------
# Estado del servicio
# --------------------------------------------------------------------------


@app.get("/health", tags=["estado"])
async def health() -> dict[str, Any]:
    """Verifica que la integración con Prolog responde.

    Lo usan el healthcheck de Docker y el CI.
    """
    if not motor.disponible:
        raise HTTPException(
            status_code=503,
            detail={"prolog": "no disponible", "error": motor.error},
        )
    return {
        "estado": "ok",
        "prolog": "conectado",
        "version_motor": motor.version(),
        "archivo": str(motor.archivo),
    }


# --------------------------------------------------------------------------
# Casos
# --------------------------------------------------------------------------


@app.get("/api/casos", tags=["casos"])
async def listar_casos() -> list[dict[str, Any]]:
    """Casos disponibles con su estado de avance.

    TODO(backend): agregar filtro por dificultad y por estado.
    """
    filas = consultar(
        "api_caso(M, Id, Titulo, Descripcion, Dificultad, Estado, NS, NE, NL, ND)"
    )
    return [
        {
            "id": fila["Id"],
            "modulo": fila["M"],
            "titulo": fila["Titulo"],
            "descripcion": fila["Descripcion"],
            "dificultad": fila["Dificultad"],
            "estado": fila["Estado"],
            "conteos": {
                "sospechosos": fila["NS"],
                "evidencias": fila["NE"],
                "lugares": fila["NL"],
                "declaraciones": fila["ND"],
            },
        }
        for fila in filas
    ]


@app.get("/api/casos/{caso_id}", tags=["casos"])
async def obtener_caso(caso_id: str) -> dict[str, Any]:
    """Descripción inicial del incidente."""
    caso_id = exigir_caso(caso_id)
    filas = consultar(
        f"api_caso({caso_id}, Id, Titulo, Descripcion, Dificultad, Estado, NS, NE, NL, ND)"
    )
    if not filas:
        raise HTTPException(status_code=404, detail=f"El caso '{caso_id}' no existe")
    fila = filas[0]
    return {
        "id": fila["Id"],
        "titulo": fila["Titulo"],
        "descripcion": fila["Descripcion"],
        "dificultad": fila["Dificultad"],
        "estado": fila["Estado"],
        "conteos": {
            "sospechosos": fila["NS"],
            "evidencias": fila["NE"],
            "lugares": fila["NL"],
            "declaraciones": fila["ND"],
        },
    }


@app.get("/api/casos/{caso_id}/sospechosos", tags=["investigación"])
async def listar_sospechosos(caso_id: str) -> list[dict[str, Any]]:
    """Sospechosos con su nivel de sospecha, de mayor a menor.

    TODO(backend): que los indicios no se pidan en una segunda consulta.
    """
    caso_id = exigir_caso(caso_id)
    sospechosos = consultar(f"api_sospechoso({caso_id}, Persona, Nivel, Puntaje)")
    indicios = consultar(f"api_indicio({caso_id}, Persona, Indicio)")
    por_persona: dict[str, list[str]] = {}
    for fila in indicios:
        por_persona.setdefault(fila["Persona"], []).append(fila["Indicio"])
    return [
        {
            "persona": fila["Persona"],
            "nivel_sospecha": fila["Nivel"],
            "puntaje": fila["Puntaje"],
            "indicios": por_persona.get(fila["Persona"], []),
        }
        for fila in sospechosos
    ]


@app.get("/api/casos/{caso_id}/evidencias", tags=["investigación"])
async def listar_evidencias(caso_id: str) -> list[dict[str, Any]]:
    """Evidencias del caso y a quién incriminan.

    TODO(backend): el enunciado pide descubrir la información poco a poco.
    Falta el parámetro para devolver solo las evidencias ya examinadas.
    """
    caso_id = exigir_caso(caso_id)
    evidencias = consultar(
        f"api_evidencia({caso_id}, Id, Tipo, Lugar, Hora, Descripcion, Directa)"
    )
    vinculos = consultar(f"api_evidencia_incrimina({caso_id}, Id, Persona)")
    incriminados: dict[str, list[str]] = {}
    for fila in vinculos:
        incriminados.setdefault(fila["Id"], []).append(fila["Persona"])
    return [
        {
            "id": fila["Id"],
            "tipo": fila["Tipo"],
            "lugar": fila["Lugar"],
            "hora": fila["Hora"],
            "descripcion": fila["Descripcion"],
            "es_directa": fila["Directa"] == "si",
            "incrimina": incriminados.get(fila["Id"], []),
        }
        for fila in evidencias
    ]


@app.get("/api/casos/{caso_id}/lugares", tags=["investigación"])
async def listar_lugares(caso_id: str) -> list[dict[str, Any]]:
    """Lugares relacionados con el caso."""
    caso_id = exigir_caso(caso_id)
    return [
        {
            "nombre": fila["Nombre"],
            "descripcion": fila["Descripcion"],
            "es_escena": fila["EsEscena"] == "si",
        }
        for fila in consultar(f"api_lugar({caso_id}, Nombre, Descripcion, EsEscena)")
    ]


@app.get("/api/casos/{caso_id}/declaraciones", tags=["investigación"])
async def listar_declaraciones(caso_id: str) -> list[dict[str, Any]]:
    """Declaraciones recogidas en el caso.

    TODO(backend): endpoint de interrogatorio (una declaración a la vez).
    """
    caso_id = exigir_caso(caso_id)
    return [
        {"id": fila["Id"], "autor": fila["Autor"], "contenido": fila["Contenido"]}
        for fila in consultar(f"api_declaracion({caso_id}, Id, Autor, Contenido)")
    ]


@app.get("/api/casos/{caso_id}/coartadas", tags=["investigación"])
async def listar_coartadas(caso_id: str) -> list[dict[str, Any]]:
    """Coartadas y por qué el motor las valida o las descarta."""
    caso_id = exigir_caso(caso_id)
    return [
        {
            "persona": fila["Persona"],
            "estado": fila["Estado"],
            "detalle": fila["Detalle"],
        }
        for fila in consultar(f"api_coartada({caso_id}, Persona, Estado, Detalle)")
    ]


@app.get("/api/casos/{caso_id}/motivos", tags=["investigación"])
async def listar_motivos(caso_id: str) -> list[dict[str, Any]]:
    """Motivos, declarados o deducidos de las relaciones con la víctima."""
    caso_id = exigir_caso(caso_id)
    return [
        {"persona": fila["Persona"], "motivo": fila["Motivo"]}
        for fila in consultar(f"api_motivo({caso_id}, Persona, Motivo)")
    ]


@app.get("/api/casos/{caso_id}/contradicciones", tags=["investigación"])
async def listar_contradicciones(caso_id: str) -> list[dict[str, Any]]:
    """Contradicciones detectadas por el motor."""
    caso_id = exigir_caso(caso_id)
    return [
        {"tipo": fila["Tipo"], "a": fila["A"], "b": fila["B"]}
        for fila in consultar(f"api_contradiccion({caso_id}, Tipo, A, B)")
    ]


@app.get("/api/casos/{caso_id}/linea-temporal", tags=["investigación"])
async def linea_temporal(caso_id: str) -> list[dict[str, Any]]:
    """Eventos conocidos del caso, ordenados por hora."""
    caso_id = exigir_caso(caso_id)
    return [
        {"hora": fila["Hora"], "tipo": fila["Tipo"], "detalle": fila["Detalle"]}
        for fila in consultar(f"api_evento({caso_id}, Hora, Tipo, Detalle)")
    ]


@app.get("/api/casos/{caso_id}/pistas", tags=["investigación"])
async def listar_pistas(caso_id: str) -> list[str]:
    """Pistas derivadas del estado del razonamiento.

    TODO(backend): entregar una pista a la vez y descontar puntaje.
    """
    caso_id = exigir_caso(caso_id)
    return [fila["Pista"] for fila in consultar(f"api_pista({caso_id}, Pista)")]


@app.get("/api/casos/{caso_id}/conclusion", tags=["conclusión"])
async def obtener_conclusion(caso_id: str) -> dict[str, Any]:
    """Conclusión del caso con la explicación de las reglas activadas.

    TODO(backend): armar con esto el informe final del caso.
    """
    caso_id = exigir_caso(caso_id)
    filas = consultar(f"api_conclusion({caso_id}, Clave, Valor)")
    responsable = next(
        (f["Valor"] for f in filas if f["Clave"] == "responsable"), "ninguno"
    )
    principales = [f["Valor"] for f in filas if f["Clave"] == "principal"]
    complices = [f["Valor"] for f in filas if f["Clave"] == "complice"]

    explicaciones: dict[str, list[dict[str, str]]] = {}
    for fila in consultar(f"api_explicacion({caso_id}, Persona, Regla, Detalle)"):
        explicaciones.setdefault(fila["Persona"], []).append(
            {"regla": fila["Regla"], "detalle": fila["Detalle"]}
        )

    veredictos = [
        {
            "persona": fila["Persona"],
            "veredicto": fila["Veredicto"],
            "nivel_sospecha": fila["Nivel"],
            "puntaje": fila["Puntaje"],
            "reglas_activadas": explicaciones.get(fila["Persona"], []),
        }
        for fila in consultar(
            f"api_veredicto({caso_id}, Persona, Veredicto, Nivel, Puntaje)"
        )
    ]

    return {
        "caso": caso_id,
        "concluye": responsable != "ninguno",
        "responsable": None if responsable == "ninguno" else responsable,
        "sospechosos_principales": principales,
        "posibles_complices": complices,
        "veredictos": veredictos,
    }


@app.post("/api/casos/{caso_id}/acusacion", tags=["conclusión"])
async def acusar(caso_id: str, acusacion: Acusacion) -> dict[str, Any]:
    """Emite una acusación y la califica contra la conclusión del motor.

    TODO(backend): registrarla en la bitácora de investigación. Por ahora no se
    persiste nada.
    """
    caso_id = exigir_caso(caso_id)
    sospechoso = atomo(acusacion.sospechoso, "sospechoso")
    filas = consultar(f"api_acusacion({caso_id}, {sospechoso}, Veredicto, Responsable)")
    if not filas:
        raise HTTPException(status_code=500, detail="El motor no evaluó la acusación")
    fila = filas[0]
    if fila["Veredicto"] == "persona_desconocida":
        raise HTTPException(
            status_code=404,
            detail=f"'{sospechoso}' no es una persona de este caso",
        )
    responsable = fila["Responsable"]
    reglas = [
        {"regla": f["Regla"], "detalle": f["Detalle"]}
        for f in consultar(f"api_explicacion({caso_id}, {sospechoso}, Regla, Detalle)")
    ]
    return {
        "caso": caso_id,
        "acusado": sospechoso,
        "veredicto": fila["Veredicto"],
        "responsable_segun_el_motor": None if responsable == "ninguno" else responsable,
        "reglas_activadas": reglas,
    }


# --------------------------------------------------------------------------
# Módulo administrativo
# --------------------------------------------------------------------------


@app.get("/api/admin/estado", tags=["administración"])
async def estado_del_proyecto() -> dict[str, Any]:
    """Estado de los casos contra los mínimos del enunciado, para el módulo
    administrativo.

    TODO(backend): contar también las reglas de inferencia propias de cada caso.
    """
    minimos = consultar("minimos_requeridos(S, E, L, D, R)")
    fila_min = minimos[0] if minimos else {}
    casos = await listar_casos()
    return {
        "minimos_por_caso": {
            "sospechosos": fila_min.get("S"),
            "evidencias": fila_min.get("E"),
            "lugares": fila_min.get("L"),
            "declaraciones": fila_min.get("D"),
            "reglas_de_inferencia": fila_min.get("R"),
        },
        "casos": casos,
        "prolog": {"disponible": motor.disponible, "error": motor.error},
    }
