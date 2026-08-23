"""API de Logic Detective.

Cada endpoint consulta Prolog a través de PySwip. Los endpoints de solo
lectura (sospechosos, evidencias, etc.) devuelven todo el caso; los de
`investigaciones.py` agregan el descubrimiento progresivo y la bitácora que
pide el enunciado. Lo que quede pendiente sigue marcado con TODO(backend).

Acá no se decide nada: si hace falta una conclusión nueva se agrega un
predicado api_* plano en prolog/logic_detective.pl y este archivo solo recoge
las filas.

Documentación interactiva: http://localhost:8000/docs
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .investigaciones import COSTO_PISTA, Investigacion, almacen
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
    version="1.0.0",
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


def casos_de_ejemplo() -> set[str]:
    """Casos de referencia, que no cuentan entre los tres entregables.

    No tienen que alcanzar los mínimos, así que `estado_caso/3` los reporta
    incompletos. La interfaz necesita saberlo para no presentarlos como trabajo
    a medio hacer en el módulo administrativo.
    """
    return {fila["M"] for fila in consultar("api_caso_de_ejemplo(M)")}


def exigir_investigacion(caso_id: str, investigacion_id: str) -> Investigacion:
    """Valida que la investigación exista y pertenezca a este caso."""
    investigacion = almacen.obtener(investigacion_id)
    if investigacion is None or investigacion.caso_id != caso_id:
        raise HTTPException(
            status_code=404,
            detail=f"La investigación '{investigacion_id}' no existe para el caso '{caso_id}'",
        )
    return investigacion


class Acusacion(BaseModel):
    """Cuerpo de POST /api/casos/{caso_id}/acusacion."""

    sospechoso: str
    investigacion_id: Optional[str] = None


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
async def listar_casos(
    dificultad: Optional[str] = None, estado: Optional[str] = None
) -> list[dict[str, Any]]:
    """Casos disponibles con su estado de avance.

    `dificultad` (facil|media|dificil) y `estado` (pendiente|incompleto|
    completo) filtran el listado; sin ellos devuelve todos, como antes.
    """
    if dificultad is not None:
        dificultad = atomo(dificultad, "dificultad")
    if estado is not None:
        estado = atomo(estado, "estado")
    filas = consultar(
        "api_caso(M, Id, Titulo, Descripcion, Dificultad, Estado, NS, NE, NL, ND)"
    )
    ejemplos = casos_de_ejemplo()
    if dificultad is not None:
        filas = [f for f in filas if f["Dificultad"] == dificultad]
    if estado is not None:
        filas = [f for f in filas if f["Estado"] == estado]
    return [
        {
            "id": fila["Id"],
            "modulo": fila["M"],
            "titulo": fila["Titulo"],
            "descripcion": fila["Descripcion"],
            "dificultad": fila["Dificultad"],
            "estado": fila["Estado"],
            "es_ejemplo": fila["Id"] in ejemplos,
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
        "es_ejemplo": fila["Id"] in casos_de_ejemplo(),
        "conteos": {
            "sospechosos": fila["NS"],
            "evidencias": fila["NE"],
            "lugares": fila["NL"],
            "declaraciones": fila["ND"],
        },
    }


# --------------------------------------------------------------------------
# Investigaciones — descubrimiento progresivo y bitácora
# --------------------------------------------------------------------------
#
# Una investigación es una partida sobre un caso. El enunciado pide que el
# usuario no reciba toda la información desde el inicio y que cada acción
# quede registrada en una bitácora; acá vive el estado que hace eso posible.
#
# Los endpoints de solo lectura (sospechosos, evidencias, lugares, etc.)
# siguen funcionando sin `investigacion_id` y devuelven todo, para no romper
# el uso administrativo ni las integraciones existentes. Pasando una
# investigación, además registran la acción correspondiente en su bitácora;
# evidencias y declaraciones, que se descubren de a una, además filtran a lo
# ya examinado o interrogado.


@app.post("/api/casos/{caso_id}/investigaciones", tags=["investigaciones"])
async def crear_investigacion(caso_id: str) -> dict[str, Any]:
    """Inicia una investigación nueva sobre un caso."""
    caso_id = exigir_caso(caso_id)
    investigacion = almacen.crear(caso_id)
    return {
        "investigacion_id": investigacion.id,
        "caso_id": caso_id,
        "puntaje": investigacion.puntaje,
    }


@app.get(
    "/api/casos/{caso_id}/investigaciones/{investigacion_id}/bitacora",
    tags=["investigaciones"],
)
async def obtener_bitacora(caso_id: str, investigacion_id: str) -> dict[str, Any]:
    """Acciones registradas durante la investigación, en el orden en que ocurrieron."""
    caso_id = exigir_caso(caso_id)
    investigacion = exigir_investigacion(caso_id, investigacion_id)
    return {
        "investigacion_id": investigacion.id,
        "caso_id": caso_id,
        "puntaje": investigacion.puntaje,
        "acciones": [accion.a_dict() for accion in investigacion.bitacora],
    }


@app.get(
    "/api/casos/{caso_id}/investigaciones/{investigacion_id}/informe",
    tags=["investigaciones"],
)
async def informe_final(caso_id: str, investigacion_id: str) -> dict[str, Any]:
    """Informe final de la investigación: avance, bitácora y conclusión del motor.

    Reutiliza `obtener_conclusion` en vez de repetir las consultas: la
    conclusión no depende de la investigación, solo de las reglas del caso.
    """
    caso_id = exigir_caso(caso_id)
    investigacion = exigir_investigacion(caso_id, investigacion_id)

    total_evidencias = len(consultar(f"api_evidencia({caso_id}, Id, _, _, _, _, _)"))
    total_declaraciones = len(consultar(f"api_declaracion({caso_id}, Id, _, _)"))
    total_pistas = len(consultar(f"api_pista({caso_id}, _)"))

    return {
        "caso": caso_id,
        "investigacion_id": investigacion.id,
        "puntaje_final": investigacion.puntaje,
        "avance": {
            "evidencias_examinadas": len(investigacion.evidencias_examinadas),
            "evidencias_totales": total_evidencias,
            "declaraciones_interrogadas": len(investigacion.declaraciones_interrogadas),
            "declaraciones_totales": total_declaraciones,
            "pistas_usadas": len(investigacion.pistas_usadas),
            "pistas_totales": total_pistas,
        },
        "bitacora": [accion.a_dict() for accion in investigacion.bitacora],
        "conclusion": await obtener_conclusion(caso_id),
    }


# --------------------------------------------------------------------------
# Investigación de un caso
# --------------------------------------------------------------------------


@app.get("/api/casos/{caso_id}/sospechosos", tags=["investigación"])
async def listar_sospechosos(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Sospechosos con su nivel de sospecha, de mayor a menor.

    TODO(backend): que los indicios no se pidan en una segunda consulta.
    """
    caso_id = exigir_caso(caso_id)
    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        investigacion.registrar("consultar", "consultó la lista de sospechosos")
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
async def listar_evidencias(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Evidencias del caso y a quién incriminan.

    Sin `investigacion_id` devuelve todas (uso administrativo). Dentro de una
    investigación, solo las que ya se examinaron con
    `POST .../evidencias/{id}/examinar`: el enunciado pide que el usuario
    descubra la información poco a poco, no que la reciba de golpe.
    """
    caso_id = exigir_caso(caso_id)
    evidencias = consultar(
        f"api_evidencia({caso_id}, Id, Tipo, Lugar, Hora, Descripcion, Directa)"
    )
    vinculos = consultar(f"api_evidencia_incrimina({caso_id}, Id, Persona)")
    incriminados: dict[str, list[str]] = {}
    for fila in vinculos:
        incriminados.setdefault(fila["Id"], []).append(fila["Persona"])

    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        evidencias = [
            fila
            for fila in evidencias
            if fila["Id"] in investigacion.evidencias_examinadas
        ]

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


@app.post(
    "/api/casos/{caso_id}/investigaciones/{investigacion_id}/evidencias/{evidencia_id}/examinar",
    tags=["investigaciones"],
)
async def examinar_evidencia(
    caso_id: str, investigacion_id: str, evidencia_id: str
) -> dict[str, Any]:
    """Marca una evidencia como examinada, la entrega y registra la acción."""
    caso_id = exigir_caso(caso_id)
    investigacion = exigir_investigacion(caso_id, investigacion_id)
    evidencia_id = atomo(evidencia_id, "evidencia_id")
    filas = consultar(
        f"api_evidencia({caso_id}, {evidencia_id}, Tipo, Lugar, Hora, Descripcion, Directa)"
    )
    if not filas:
        raise HTTPException(
            status_code=404,
            detail=f"La evidencia '{evidencia_id}' no existe en este caso",
        )
    fila = filas[0]
    incriminados = [
        f["Persona"]
        for f in consultar(
            f"api_evidencia_incrimina({caso_id}, {evidencia_id}, Persona)"
        )
    ]
    investigacion.evidencias_examinadas.add(evidencia_id)
    investigacion.registrar("consultar", f"examinó la evidencia {evidencia_id}")
    return {
        "id": evidencia_id,
        "tipo": fila["Tipo"],
        "lugar": fila["Lugar"],
        "hora": fila["Hora"],
        "descripcion": fila["Descripcion"],
        "es_directa": fila["Directa"] == "si",
        "incrimina": incriminados,
    }


@app.get("/api/casos/{caso_id}/lugares", tags=["investigación"])
async def listar_lugares(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Lugares relacionados con el caso."""
    caso_id = exigir_caso(caso_id)
    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        investigacion.registrar("consultar", "consultó los lugares del caso")
    return [
        {
            "nombre": fila["Nombre"],
            "descripcion": fila["Descripcion"],
            "es_escena": fila["EsEscena"] == "si",
        }
        for fila in consultar(f"api_lugar({caso_id}, Nombre, Descripcion, EsEscena)")
    ]


@app.get("/api/casos/{caso_id}/declaraciones", tags=["investigación"])
async def listar_declaraciones(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Declaraciones recogidas en el caso.

    Sin `investigacion_id` devuelve todas. Dentro de una investigación, solo
    las que ya se interrogaron con `POST .../declaraciones/{id}/interrogar`.
    """
    caso_id = exigir_caso(caso_id)
    declaraciones = consultar(f"api_declaracion({caso_id}, Id, Autor, Contenido)")
    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        declaraciones = [
            fila
            for fila in declaraciones
            if fila["Id"] in investigacion.declaraciones_interrogadas
        ]
    return [
        {"id": fila["Id"], "autor": fila["Autor"], "contenido": fila["Contenido"]}
        for fila in declaraciones
    ]


@app.post(
    "/api/casos/{caso_id}/investigaciones/{investigacion_id}/declaraciones/{declaracion_id}/interrogar",
    tags=["investigaciones"],
)
async def interrogar_declaracion(
    caso_id: str, investigacion_id: str, declaracion_id: str
) -> dict[str, Any]:
    """Marca una declaración como interrogada, la entrega y registra la acción."""
    caso_id = exigir_caso(caso_id)
    investigacion = exigir_investigacion(caso_id, investigacion_id)
    declaracion_id = atomo(declaracion_id, "declaracion_id")
    filas = consultar(f"api_declaracion({caso_id}, {declaracion_id}, Autor, Contenido)")
    if not filas:
        raise HTTPException(
            status_code=404,
            detail=f"La declaración '{declaracion_id}' no existe en este caso",
        )
    fila = filas[0]
    investigacion.declaraciones_interrogadas.add(declaracion_id)
    investigacion.registrar(
        "interrogar", f"interrogó la declaración {declaracion_id} de {fila['Autor']}"
    )
    return {
        "id": declaracion_id,
        "autor": fila["Autor"],
        "contenido": fila["Contenido"],
    }


@app.get("/api/casos/{caso_id}/coartadas", tags=["investigación"])
async def listar_coartadas(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Coartadas y por qué el motor las valida o las descarta."""
    caso_id = exigir_caso(caso_id)
    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        investigacion.registrar("analizar", "analizó las coartadas")
    return [
        {
            "persona": fila["Persona"],
            "estado": fila["Estado"],
            "detalle": fila["Detalle"],
        }
        for fila in consultar(f"api_coartada({caso_id}, Persona, Estado, Detalle)")
    ]


@app.get("/api/casos/{caso_id}/motivos", tags=["investigación"])
async def listar_motivos(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Motivos, declarados o deducidos de las relaciones con la víctima."""
    caso_id = exigir_caso(caso_id)
    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        investigacion.registrar("analizar", "analizó los motivos")
    return [
        {"persona": fila["Persona"], "motivo": fila["Motivo"]}
        for fila in consultar(f"api_motivo({caso_id}, Persona, Motivo)")
    ]


@app.get("/api/casos/{caso_id}/relaciones", tags=["investigación"])
async def listar_relaciones(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Vínculos entre las personas involucradas.

    `es_conflictiva` marca las relaciones que el motor usa para deducir un
    motivo cuando no está declarado (ex_pareja, deudor, rival, heredero).
    """
    caso_id = exigir_caso(caso_id)
    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        investigacion.registrar(
            "consultar", "consultó las relaciones entre las personas"
        )
    return [
        {
            "persona": fila["Persona"],
            "con_quien": fila["ConQuien"],
            "tipo": fila["Tipo"],
            "es_conflictiva": fila["Conflictiva"] == "si",
            "es_con_la_victima": fila["Victima"] == "si",
        }
        for fila in consultar(
            f"api_relacion({caso_id}, Persona, ConQuien, Tipo, Conflictiva, Victima)"
        )
    ]


@app.get("/api/casos/{caso_id}/oportunidades", tags=["investigación"])
async def listar_oportunidades(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Quiénes pudieron cometer el incidente: estuvieron o pudieron estar en la
    escena y no tienen una coartada que los descarte."""
    caso_id = exigir_caso(caso_id)
    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        investigacion.registrar("analizar", "analizó las oportunidades")
    return [
        {"persona": fila["Persona"], "lugar": fila["Lugar"]}
        for fila in consultar(f"api_oportunidad({caso_id}, Persona, Lugar)")
    ]


@app.get("/api/casos/{caso_id}/contradicciones", tags=["investigación"])
async def listar_contradicciones(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Contradicciones detectadas por el motor."""
    caso_id = exigir_caso(caso_id)
    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        investigacion.registrar("deducir", "buscó contradicciones")
    return [
        {"tipo": fila["Tipo"], "a": fila["A"], "b": fila["B"]}
        for fila in consultar(f"api_contradiccion({caso_id}, Tipo, A, B)")
    ]


@app.get("/api/casos/{caso_id}/linea-temporal", tags=["investigación"])
async def linea_temporal(
    caso_id: str, investigacion_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Eventos conocidos del caso, ordenados por hora."""
    caso_id = exigir_caso(caso_id)
    if investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, investigacion_id)
        investigacion.registrar("analizar", "revisó la línea temporal")
    return [
        {"hora": fila["Hora"], "tipo": fila["Tipo"], "detalle": fila["Detalle"]}
        for fila in consultar(f"api_evento({caso_id}, Hora, Tipo, Detalle)")
    ]


@app.get("/api/casos/{caso_id}/pistas", tags=["investigación"])
async def listar_pistas(caso_id: str) -> list[str]:
    """Todas las pistas que el motor puede dar para este caso.

    Uso administrativo o de referencia: devuelve todas de una vez, sin costo.
    Dentro de una investigación, pedilas de a una con
    `POST .../pistas/siguiente`, que sí descuenta puntaje por pedirla.
    """
    caso_id = exigir_caso(caso_id)
    return [fila["Pista"] for fila in consultar(f"api_pista({caso_id}, Pista)")]


@app.post(
    "/api/casos/{caso_id}/investigaciones/{investigacion_id}/pistas/siguiente",
    tags=["investigaciones"],
)
async def pedir_pista(caso_id: str, investigacion_id: str) -> dict[str, Any]:
    """Entrega la próxima pista no usada y descuenta puntaje por pedirla.

    Compara por el texto de la pista, no por posición en la lista: es lo único
    estable que devuelve Prolog, ya que `pista/1` no numera sus soluciones.
    """
    caso_id = exigir_caso(caso_id)
    investigacion = exigir_investigacion(caso_id, investigacion_id)
    todas = [fila["Pista"] for fila in consultar(f"api_pista({caso_id}, Pista)")]
    disponibles = [p for p in todas if p not in investigacion.pistas_usadas]
    if not disponibles:
        raise HTTPException(
            status_code=404, detail="No quedan más pistas para este caso"
        )
    pista = disponibles[0]
    investigacion.pistas_usadas.append(pista)
    investigacion.puntaje = max(0, investigacion.puntaje - COSTO_PISTA)
    investigacion.registrar("pedir_ayuda", f"pidió la pista: {pista}")
    return {
        "pista": pista,
        "puntaje": investigacion.puntaje,
        "pistas_restantes": len(disponibles) - 1,
    }


@app.get("/api/casos/{caso_id}/conclusion", tags=["conclusión"])
async def obtener_conclusion(caso_id: str) -> dict[str, Any]:
    """Conclusión del caso con la explicación de las reglas activadas.

    La usa también `informe_final` para el informe de cierre de la
    investigación: la conclusión no depende de qué usuario la pida.
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

    Con `investigacion_id` en el cuerpo, registra la acusación (y su
    veredicto) como última entrada de la bitácora.
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
    if acusacion.investigacion_id is not None:
        investigacion = exigir_investigacion(caso_id, acusacion.investigacion_id)
        investigacion.registrar(
            "acusar", f"acusó a {sospechoso}: veredicto {fila['Veredicto']}"
        )
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
    """Estado de los casos contra los cinco mínimos del enunciado, para el
    módulo administrativo.

    Las reglas de inferencia propias se agregan acá y no en `/api/casos`: son la
    única cuenta que exige recorrer las cláusulas de cada caso, y solo esta
    vista las necesita.
    """
    minimos = consultar("minimos_requeridos(S, E, L, D, R)")
    fila_min = minimos[0] if minimos else {}
    casos = await listar_casos()
    reglas = {fila["M"]: fila["N"] for fila in consultar("api_reglas_propias(M, N)")}
    for caso in casos:
        caso["conteos"]["reglas_de_inferencia"] = reglas.get(caso["id"])
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
