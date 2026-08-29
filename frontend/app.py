"""Interfaz web de Logic Detective.

Dos módulos, como pide el enunciado:

  /investigacion   resolver casos
  /admin           estado de los casos

Este servidor no razona: todo lo pide al backend, que lo consulta a Prolog. Si
te ves calculando algo acá, va en Prolog.

Lo único que guarda es qué investigación tiene abierta este navegador en cada
caso, en la cookie de sesión. El estado de la investigación —qué se descubrió,
el puntaje, la bitácora— vive en el backend; acá solo se recuerda el
identificador para poder volver a pedirlo.

Levantar en desarrollo:
    BACKEND_URL=http://localhost:8000 python frontend/app.py
"""

from __future__ import annotations

import os
import random
import re
from functools import wraps
from typing import Any
from urllib.parse import urlencode

import requests
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)

# Firma la cookie de sesión (dónde vive el id de cada investigación) y los
# mensajes flash. En el despliegue hay que pasar SECRET_KEY por variable de
# entorno: si cambia, se pierden las investigaciones abiertas.
app.secret_key = os.environ.get("SECRET_KEY", "logic-detective-dev")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 10


class ErrorBackend(Exception):
    """El backend no respondió o respondió con error.

    `codigo` es el estado HTTP cuando hubo respuesta, o None si no se pudo
    contactar al backend. Las vistas lo miran para distinguir un 404 —una
    investigación que ya no existe— de una caída del servicio.
    """

    def __init__(self, mensaje: str, codigo: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo = codigo


def api(
    ruta: str,
    metodo: str = "GET",
    json: dict | None = None,
    **parametros: Any,
) -> Any:
    """Llama al backend y devuelve el JSON.

    Los `parametros` van como query string; los vacíos se descartan, así no se
    manda `?investigacion_id=None`. Centraliza el manejo de errores para que,
    si el backend o Prolog están caídos, la interfaz muestre un mensaje y no
    una traza.
    """
    consulta = {clave: valor for clave, valor in parametros.items() if valor}
    if consulta:
        ruta = f"{ruta}?{urlencode(consulta)}"
    try:
        respuesta = requests.request(
            metodo, f"{BACKEND_URL}{ruta}", json=json, timeout=TIMEOUT
        )
    except requests.RequestException as exc:
        raise ErrorBackend(f"No se pudo contactar al backend ({BACKEND_URL}): {exc}")
    if respuesta.status_code >= 400:
        detalle = respuesta.text
        try:
            detalle = respuesta.json().get("detail", detalle)
        except ValueError:
            pass
        raise ErrorBackend(f"{respuesta.status_code}: {detalle}", respuesta.status_code)
    return respuesta.json()


def api_opcional(ruta: str, por_defecto: Any, **parametros: Any) -> Any:
    """Como api() pero devuelve un valor por defecto en lugar de fallar.

    Para las secciones de la vista de caso: que falte una no debería tumbar la
    página entera.
    """
    try:
        return api(ruta, **parametros)
    except ErrorBackend:
        return por_defecto


def ruta_investigacion(caso_id: str, investigacion_id: str) -> str:
    """Prefijo de los endpoints de una investigación."""
    return f"/api/casos/{caso_id}/investigaciones/{investigacion_id}"


@app.template_filter("nombre")
def nombre_legible(atomo: Any) -> str:
    """`victor_cordero` -> `Victor Cordero`.

    Prolog trabaja con átomos en snake_case y sin acentos; para leerlos en
    pantalla alcanza con esto. El valor que se le manda de vuelta al backend
    siempre es el átomo, nunca esta versión.
    """
    return str(atomo).replace("_", " ").title() if atomo else ""


#: Cómo se lee cada indicio del motor. Las claves son los átomos que devuelve
#: `api_indicio/3`; lo que no esté acá cae en el filtro `nombre`, así que un
#: indicio nuevo en Prolog se ve igual —feo pero legible— sin tocar esto.
ETIQUETAS_INDICIO = {
    "acceso": "tenía acceso",
    "coartada_invalida": "coartada inválida",
    "evidencia_directa": "evidencia directa",
    "informacion_falsa": "dio información falsa",
    "medios": "tenía los medios",
    "motivo": "tenía motivo",
    "multiples_evidencias": "varias evidencias",
    "oportunidad": "tuvo oportunidad",
}

#: Las pistas llegan como términos de Prolog (`revisar_evidencia(e3)`). Acá se
#: leen en castellano; el término se sigue mostrando al lado, que es lo que
#: prueba que la pista la eligió el motor y no la interfaz. El segundo campo
#: dice si el argumento es una persona (se formatea con `nombre`) o un
#: identificador, que se deja tal cual.
PATRONES_PISTA = {
    "revisar_evidencia": ("Revisá la evidencia {}.", False),
    "revisar_coartada_de": ("Revisá la coartada de {}.", True),
    "revisar_declaraciones_de": ("Revisá las declaraciones de {}.", True),
    "revisar_relacion_con_la_victima": (
        "Revisá la relación de {} con la víctima.",
        True,
    ),
}

#: `functor(argumento)`, la forma de todas las pistas de `api_pista/2`.
TERMINO_PISTA = re.compile(r"^([a-z_]+)\(([a-zA-Z0-9_]+)\)$")


@app.template_filter("indicio")
def indicio_legible(atomo: Any) -> str:
    """`coartada_invalida` -> `coartada inválida`."""
    return ETIQUETAS_INDICIO.get(str(atomo), nombre_legible(atomo))


@app.template_filter("pista")
def pista_legible(pista: str) -> str:
    """`revisar_evidencia(e3)` -> `Revisá la evidencia e3.`

    Devuelve la pista tal cual si no reconoce la forma del término: es mejor
    mostrarla cruda que perderla.
    """
    coincide = TERMINO_PISTA.match(str(pista).strip())
    if coincide is None:
        return str(pista)
    plantilla = PATRONES_PISTA.get(coincide.group(1))
    if plantilla is None:
        return str(pista)
    formato, es_persona = plantilla
    argumento = coincide.group(2)
    return formato.format(nombre_legible(argumento) if es_persona else argumento)


# --------------------------------------------------------------------------
# Filtros del listado de casos
# --------------------------------------------------------------------------
#
# El filtrado lo hace el backend (`/api/casos?dificultad=&estado=`). Acá solo
# se valida el parámetro antes de reenviarlo —la URL la puede escribir el
# usuario, y el backend responde 400 a lo que no sea un átomo de Prolog— y se
# cuentan los casos de cada valor para los contadores de los chips, que
# necesitan la lista completa.

DIFICULTADES = ("facil", "media", "dificil")
ESTADOS = ("completo", "incompleto", "pendiente")

ETIQUETAS_DIFICULTAD = {"facil": "Fácil", "media": "Media", "dificil": "Difícil"}
ETIQUETAS_ESTADO = {
    "completo": "Completo",
    "incompleto": "Incompleto",
    "pendiente": "Pendiente",
}

#: Acciones de análisis del panel de investigación. La clave es el recurso del
#: backend; cada visita a `?analisis=<clave>` consulta ese endpoint con la
#: investigación abierta, y el backend lo registra en la bitácora. Por eso son
#: acciones explícitas del usuario y no se cargan todas al abrir la página: la
#: bitácora tiene que decir qué hizo el detective, no qué renderizó Flask.
ANALISIS = {
    "sospechosos": {
        "titulo": "Sospechosos",
        "boton": "Evaluar a los sospechosos",
        "detalle": "Nivel de sospecha e indicios que reunió el motor.",
    },
    "lugares": {
        "titulo": "Lugares",
        "boton": "Recorrer los lugares",
        "detalle": "Escenario del incidente y lugares relacionados.",
    },
    "coartadas": {
        "titulo": "Coartadas",
        "boton": "Verificar las coartadas",
        "detalle": "Qué coartada sostiene el motor y por qué.",
    },
    "relaciones": {
        "titulo": "Relaciones",
        "boton": "Revisar las relaciones",
        "detalle": "Vínculos entre las personas. Los conflictivos alimentan los motivos.",
    },
    "motivos": {
        "titulo": "Motivos",
        "boton": "Buscar motivos",
        "detalle": "Motivos declarados o deducidos de la relación con la víctima.",
    },
    "oportunidades": {
        "titulo": "Oportunidades",
        "boton": "Analizar las oportunidades",
        "detalle": "Quién pudo estar en la escena sin una coartada que lo descarte.",
    },
    "contradicciones": {
        "titulo": "Contradicciones",
        "boton": "Cruzar las declaraciones",
        "detalle": "Choques entre declaraciones y evidencias.",
    },
    "linea-temporal": {
        "titulo": "Línea temporal",
        "boton": "Reconstruir la línea temporal",
        "detalle": "Los hechos conocidos, ordenados por hora.",
    },
}

#: Prefijo con el que el backend anota una pista en la bitácora. Solo se usa
#: para no repetirlo en la lista de pistas; si cambia, se muestra la entrada
#: completa y no se rompe nada.
PREFIJO_PISTA = "pidió la pista: "

MENSAJE_VEREDICTO = {
    "correcta": "Acusación correcta: el motor también señala a {acusado}.",
    "incorrecta": "Acusación incorrecta. Para el motor el responsable es {responsable}.",
    "indeterminada": "El motor no reúne elementos suficientes para señalar a nadie.",
}


def opcion(valor: str | None, permitidos: tuple[str, ...]) -> str:
    """Normaliza un parámetro de la URL. Devuelve "" si no es uno esperado."""
    valor = (valor or "").strip().lower()
    return valor if valor in permitidos else ""


def contar_por(
    casos: list[dict[str, Any]], campo: str, valores: tuple[str, ...]
) -> dict[str, int]:
    """Cuántos casos hay de cada valor, para el contador de cada filtro."""
    return {v: sum(1 for caso in casos if caso.get(campo) == v) for v in valores}


# --------------------------------------------------------------------------
# Investigación abierta en este navegador
# --------------------------------------------------------------------------
#
# `session["investigaciones"]` es {caso_id: investigacion_id}. Una por caso:
# volver a un caso retoma la investigación donde se dejó.

CLAVE_SESION = "investigaciones"


def investigaciones_abiertas() -> dict[str, str]:
    return session.get(CLAVE_SESION, {})


def investigacion_de(caso_id: str) -> str | None:
    return investigaciones_abiertas().get(caso_id)


def recordar_investigacion(caso_id: str, investigacion_id: str) -> None:
    abiertas = dict(investigaciones_abiertas())
    abiertas[caso_id] = investigacion_id
    session[CLAVE_SESION] = abiertas


def olvidar_investigacion(caso_id: str) -> None:
    abiertas = dict(investigaciones_abiertas())
    if abiertas.pop(caso_id, None) is not None:
        session[CLAVE_SESION] = abiertas


def con_investigacion(vista):
    """Le pasa a la vista la investigación abierta del caso.

    Sin investigación abierta no hay nada que registrar en ninguna bitácora,
    así que devuelve al expediente en vez de dejar que el backend responda 404.
    """

    @wraps(vista)
    def envoltura(**valores):
        caso_id = valores["caso_id"]
        investigacion_id = investigacion_de(caso_id)
        if investigacion_id is None:
            flash("Primero hay que abrir la investigación del caso.", "error")
            return redirect(url_for("investigar_caso", caso_id=caso_id))
        return vista(investigacion_id=investigacion_id, **valores)

    return envoltura


def volver_al_caso(caso_id: str):
    """Vuelve al panel del caso conservando el análisis que estaba abierto."""
    analisis = opcion(request.form.get("analisis"), tuple(ANALISIS))
    return redirect(
        url_for("investigar_caso", caso_id=caso_id, analisis=analisis or None)
    )


# --------------------------------------------------------------------------
# Descubrimiento progresivo
# --------------------------------------------------------------------------


def descubrimiento(
    todos: list[dict[str, Any]],
    descubiertos: list[dict[str, Any]],
    visibles: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Une la lista completa con la ya descubierta, recortando el resto.

    El backend necesita dos llamadas para esto: sin `investigacion_id` devuelve
    todo (de ahí salen los identificadores para poder ofrecer la acción) y con
    él solo lo ya examinado o interrogado. Acá se juntan, y de lo que todavía
    no se descubrió sobreviven únicamente los campos `visibles` —el id, y el
    autor en las declaraciones—: así el dato que el detective no descubrió
    nunca llega al HTML.
    """
    por_id = {item["id"]: item for item in descubiertos}
    return [
        {**por_id[item["id"]], "descubierto": True}
        if item["id"] in por_id
        else {**{campo: item[campo] for campo in visibles}, "descubierto": False}
        for item in todos
    ]


def pistas_pedidas(acciones: list[dict[str, Any]]) -> list[str]:
    """Las pistas que ya se pidieron, leídas de la bitácora.

    No hace falta guardarlas acá: la bitácora del backend ya es el registro de
    lo que pasó en la investigación.
    """
    return [
        accion["detalle"].removeprefix(PREFIJO_PISTA)
        for accion in acciones
        if accion["tipo"] == "pedir_ayuda"
    ]


def pistas_restantes(restantes: int) -> str:
    """Cuántas pistas quedan, en singular o plural."""
    if restantes == 0:
        return "No quedan más pistas."
    if restantes == 1:
        return "Queda 1 pista más."
    return f"Quedan {restantes} pistas más."


def avance(elementos: list[dict[str, Any]]) -> dict[str, int]:
    """Cuántos elementos de una lista ya se descubrieron."""
    return {
        "descubiertos": sum(1 for e in elementos if e["descubierto"]),
        "total": len(elementos),
    }


# --------------------------------------------------------------------------
# Inicio
# --------------------------------------------------------------------------


@app.route("/")
def inicio():
    """Pantalla principal: nombre, propósito y casos disponibles."""
    try:
        casos = api("/api/casos")
        error = None
    except ErrorBackend as exc:
        casos, error = [], str(exc)
    return render_template("inicio.html", casos=casos, error=error)


# --------------------------------------------------------------------------
# Módulo de investigación
# --------------------------------------------------------------------------


@app.route("/investigacion")
def investigacion():
    """Listado de casos para iniciar una investigación.

    Acepta ?dificultad=facil|media|dificil y ?estado=completo|incompleto|
    pendiente, y se los reenvía al backend. Un valor que no exista se ignora en
    lugar de dar error: la URL la puede escribir el usuario a mano.
    """
    dificultad = opcion(request.args.get("dificultad"), DIFICULTADES)
    estado = opcion(request.args.get("estado"), ESTADOS)
    try:
        # Dos llamadas a propósito: los contadores de los chips cuentan sobre
        # todos los casos, no sobre los que quedaron después de filtrar.
        todos = api("/api/casos")
        casos = (
            api("/api/casos", dificultad=dificultad, estado=estado)
            if dificultad or estado
            else todos
        )
        error = None
    except ErrorBackend as exc:
        todos, casos, error = [], [], str(exc)
    return render_template(
        "investigacion.html",
        casos=casos,
        total=len(todos),
        dificultad=dificultad,
        estado=estado,
        dificultades=DIFICULTADES,
        estados=ESTADOS,
        etiquetas_dificultad=ETIQUETAS_DIFICULTAD,
        etiquetas_estado=ETIQUETAS_ESTADO,
        conteos_dificultad=contar_por(todos, "dificultad", DIFICULTADES),
        conteos_estado=contar_por(todos, "estado", ESTADOS),
        error=error,
    )


@app.route("/investigacion/aleatorio")
def caso_aleatorio():
    """Abre un caso al azar, respetando los filtros activos.

    Solo entran al sorteo los casos que ya tienen hechos cargados en Prolog:
    mandar al usuario a un caso 'pendiente' es mandarlo a una página vacía.
    """
    dificultad = opcion(request.args.get("dificultad"), DIFICULTADES)
    estado = opcion(request.args.get("estado"), ESTADOS)
    volver = url_for(
        "investigacion", dificultad=dificultad or None, estado=estado or None
    )
    try:
        casos = api("/api/casos", dificultad=dificultad, estado=estado)
    except ErrorBackend as exc:
        flash(f"No se pudo obtener la lista de casos. {exc}", "error")
        return redirect(volver)

    candidatos = [caso for caso in casos if caso.get("estado") != "pendiente"]
    if not candidatos:
        flash("No hay casos con datos cargados que coincidan con el filtro.", "error")
        return redirect(volver)
    return redirect(url_for("investigar_caso", caso_id=random.choice(candidatos)["id"]))


@app.route("/investigacion/<caso_id>")
def investigar_caso(caso_id: str):
    """Expediente del caso y panel de trabajo del detective.

    Sin investigación abierta muestra solo la portada del expediente: el
    enunciado pide que la información se descubra con acciones, no que llegue
    toda al abrir la página. Con una investigación abierta muestra el panel,
    con lo ya descubierto, las acciones disponibles y la bitácora.
    """
    try:
        caso = api(f"/api/casos/{caso_id}")
    except ErrorBackend as exc:
        return render_template("caso.html", caso=None, error=str(exc)), 404

    investigacion_id = investigacion_de(caso_id)
    if investigacion_id is None:
        return render_template("caso.html", caso=caso, investigacion=None, error=None)

    # La bitácora es la única llamada que depende solo de la investigación: si
    # responde 404, la investigación ya no existe. El backend las guarda en
    # memoria, así que un reinicio suyo deja la cookie apuntando a la nada.
    try:
        bitacora = api(f"{ruta_investigacion(caso_id, investigacion_id)}/bitacora")
    except ErrorBackend as exc:
        if exc.codigo == 404:
            olvidar_investigacion(caso_id)
            flash(
                "La investigación anterior ya no está en el servidor. "
                "Podés abrir una nueva.",
                "error",
            )
            return render_template(
                "caso.html", caso=caso, investigacion=None, error=None
            )
        return render_template(
            "caso.html", caso=caso, investigacion=None, error=str(exc)
        )

    evidencias = descubrimiento(
        api_opcional(f"/api/casos/{caso_id}/evidencias", []),
        api_opcional(
            f"/api/casos/{caso_id}/evidencias", [], investigacion_id=investigacion_id
        ),
        ("id",),
    )
    declaraciones = descubrimiento(
        api_opcional(f"/api/casos/{caso_id}/declaraciones", []),
        api_opcional(
            f"/api/casos/{caso_id}/declaraciones",
            [],
            investigacion_id=investigacion_id,
        ),
        ("id", "autor"),
    )

    # Los nombres de los sospechosos son la carátula del expediente: hacen
    # falta para poder acusar. Se piden sin `investigacion_id` —no es una
    # acción de investigación— y de la respuesta solo se usa el nombre; el
    # nivel de sospecha y los indicios los revela el análisis correspondiente.
    personas = [
        s["persona"] for s in api_opcional(f"/api/casos/{caso_id}/sospechosos", [])
    ]

    # De `/pistas` (todas, sin costo ni registro) solo se usa el total: sirve
    # para no ofrecer una pista que ya no existe. Los textos se piden de a uno,
    # y esos sí cuestan puntaje.
    total_pistas = len(api_opcional(f"/api/casos/{caso_id}/pistas", []))

    analisis = opcion(request.args.get("analisis"), tuple(ANALISIS))
    return render_template(
        "caso.html",
        caso=caso,
        error=None,
        investigacion={
            "id": investigacion_id,
            "puntaje": bitacora["puntaje"],
            "acciones": bitacora["acciones"],
            "pistas": pistas_pedidas(bitacora["acciones"]),
            "pistas_totales": total_pistas,
        },
        evidencias=evidencias,
        declaraciones=declaraciones,
        avance_evidencias=avance(evidencias),
        avance_declaraciones=avance(declaraciones),
        personas=personas,
        analisis=analisis,
        analisis_disponibles=ANALISIS,
        resultado=(
            api_opcional(
                f"/api/casos/{caso_id}/{analisis}",
                [],
                investigacion_id=investigacion_id,
            )
            if analisis
            else None
        ),
    )


@app.route("/investigacion/<caso_id>/abrir", methods=["POST"])
def abrir_investigacion(caso_id: str):
    """Abre una investigación nueva sobre el caso.

    Sirve también para reiniciar: la anterior queda en el backend, pero este
    navegador pasa a trabajar sobre la nueva, con la bitácora en blanco.
    """
    try:
        nueva = api(f"/api/casos/{caso_id}/investigaciones", metodo="POST")
    except ErrorBackend as exc:
        flash(f"No se pudo abrir la investigación. {exc}", "error")
        return redirect(url_for("investigar_caso", caso_id=caso_id))
    recordar_investigacion(caso_id, nueva["investigacion_id"])
    flash(f"Investigación abierta. Puntaje inicial: {nueva['puntaje']}.", "correcta")
    return redirect(url_for("investigar_caso", caso_id=caso_id))


@app.route(
    "/investigacion/<caso_id>/evidencias/<evidencia_id>/examinar", methods=["POST"]
)
@con_investigacion
def examinar_evidencia(caso_id: str, evidencia_id: str, investigacion_id: str):
    """Examina una evidencia: la revela y la deja anotada en la bitácora."""
    try:
        evidencia = api(
            f"{ruta_investigacion(caso_id, investigacion_id)}"
            f"/evidencias/{evidencia_id}/examinar",
            metodo="POST",
        )
        flash(
            f"Evidencia {evidencia['id']} examinada: {evidencia['tipo']}.", "correcta"
        )
    except ErrorBackend as exc:
        flash(f"No se pudo examinar la evidencia. {exc}", "error")
    return volver_al_caso(caso_id)


@app.route(
    "/investigacion/<caso_id>/declaraciones/<declaracion_id>/interrogar",
    methods=["POST"],
)
@con_investigacion
def interrogar(caso_id: str, declaracion_id: str, investigacion_id: str):
    """Interroga a quien dio una declaración: revela lo que dijo."""
    try:
        declaracion = api(
            f"{ruta_investigacion(caso_id, investigacion_id)}"
            f"/declaraciones/{declaracion_id}/interrogar",
            metodo="POST",
        )
        flash(
            f"{nombre_legible(declaracion['autor'])} declaró.",
            "correcta",
        )
    except ErrorBackend as exc:
        flash(f"No se pudo interrogar. {exc}", "error")
    return volver_al_caso(caso_id)


@app.route("/investigacion/<caso_id>/pista", methods=["POST"])
@con_investigacion
def pedir_pista(caso_id: str, investigacion_id: str):
    """Pide la próxima pista. El backend descuenta el puntaje."""
    try:
        resultado = api(
            f"{ruta_investigacion(caso_id, investigacion_id)}/pistas/siguiente",
            metodo="POST",
        )
        flash(
            f"Pista nueva. Puntaje: {resultado['puntaje']}. "
            f"{pistas_restantes(resultado['pistas_restantes'])}",
            "correcta",
        )
    except ErrorBackend as exc:
        flash(f"No se pudo pedir una pista. {exc}", "error")
    return volver_al_caso(caso_id)


@app.route("/investigacion/<caso_id>/acusacion", methods=["POST"])
def acusar(caso_id: str):
    """Emite la acusación final contra un sospechoso.

    Con una investigación abierta, la acusación y su veredicto quedan en la
    bitácora. Sin ella la acusación se evalúa igual: el endpoint del backend no
    la exige, y así sigue sirviendo para revisar un caso sin jugarlo.
    """
    sospechoso = (request.form.get("sospechoso") or "").strip()
    if not sospechoso:
        flash("Elegí a un sospechoso antes de acusar.", "error")
        return volver_al_caso(caso_id)

    cuerpo: dict[str, Any] = {"sospechoso": sospechoso}
    investigacion_id = investigacion_de(caso_id)
    if investigacion_id is not None:
        cuerpo["investigacion_id"] = investigacion_id
    try:
        resultado = api(f"/api/casos/{caso_id}/acusacion", metodo="POST", json=cuerpo)
    except ErrorBackend as exc:
        flash(f"No se pudo evaluar la acusación. {exc}", "error")
        return volver_al_caso(caso_id)

    veredicto = resultado["veredicto"]
    plantilla = MENSAJE_VEREDICTO.get(veredicto, f"Acusación {veredicto}.")
    flash(
        plantilla.format(
            acusado=nombre_legible(resultado["acusado"]),
            responsable=nombre_legible(resultado["responsable_segun_el_motor"]),
        ),
        veredicto,
    )
    return volver_al_caso(caso_id)


@app.route("/investigacion/<caso_id>/informe")
@con_investigacion
def informe(caso_id: str, investigacion_id: str):
    """Informe final: avance, bitácora y conclusión razonada del motor."""
    try:
        datos = api(f"{ruta_investigacion(caso_id, investigacion_id)}/informe")
    except ErrorBackend as exc:
        if exc.codigo == 404:
            olvidar_investigacion(caso_id)
        flash(f"No se pudo armar el informe. {exc}", "error")
        return redirect(url_for("investigar_caso", caso_id=caso_id))
    return render_template(
        "informe.html",
        informe=datos,
        caso=api_opcional(f"/api/casos/{caso_id}", None),
        caso_id=caso_id,
        error=None,
    )


# --------------------------------------------------------------------------
# Módulo administrativo
# --------------------------------------------------------------------------


def resumen_de_investigaciones() -> list[dict[str, Any]]:
    """Las investigaciones abiertas desde este navegador, con su avance.

    El backend guarda las investigaciones en memoria y sin dueño, y no expone
    un listado de todas, así que el módulo administrativo solo puede mostrar
    las de esta sesión. Alcanza para lo que pide el enunciado: llegar a la
    bitácora y al informe de una investigación en curso.
    """
    resumen = []
    for caso_id, investigacion_id in investigaciones_abiertas().items():
        bitacora = api_opcional(
            f"{ruta_investigacion(caso_id, investigacion_id)}/bitacora", None
        )
        resumen.append(
            {
                "caso_id": caso_id,
                "investigacion_id": investigacion_id,
                "vigente": bitacora is not None,
                "puntaje": bitacora["puntaje"] if bitacora else None,
                "acciones": len(bitacora["acciones"]) if bitacora else 0,
            }
        )
    return resumen


# --------------------------------------------------------------------------
# Módulo administrativo
# --------------------------------------------------------------------------
#
# Las ocho entidades comparten el mismo formulario, así que están descritas como
# datos —`ENTIDADES`— y una sola plantilla las recorre.
#
# Acá no hay ninguna regla del dominio: los valores válidos los da
# `GET /api/admin/esquema` y quien rechaza un dato inválido es el backend.


def campo(
    nombre: str,
    etiqueta: str,
    tipo: str = "texto",
    *,
    fuente: str | None = None,
    clave: bool = False,
    opcional: bool = False,
    ayuda: str = "",
    valor_de: str | None = None,
) -> dict[str, Any]:
    """Un campo del formulario de una entidad.

    `clave` marca los que forman la identidad del registro: quedan bloqueados al
    editar, porque cambiarlos no sería modificar el hecho sino reemplazarlo.
    """
    return {
        "nombre": nombre,
        "etiqueta": etiqueta,
        "tipo": tipo,
        "fuente": fuente,
        "clave": clave,
        "opcional": opcional,
        "ayuda": ayuda,
        # De qué clave de la fila se rellena al editar, si no es su mismo nombre.
        "valor_de": valor_de or nombre,
    }


ENTIDADES: dict[str, dict[str, Any]] = {
    "personas": {
        "titulo": "Personas",
        "singular": "la persona",
        "detalle": (
            "Sospechosos, testigos y víctima. El rol decide quién entra al "
            "ranking de sospecha y a quién se le exige coartada."
        ),
        "clave": ("nombre",),
        "columnas": (("nombre", "Persona", "nombre"), ("rol", "Rol", "etiqueta")),
        "campos": (
            campo(
                "nombre",
                "Identificador",
                "atomo",
                clave=True,
                ayuda="minúsculas, dígitos y guion bajo: victor_cordero",
            ),
            campo("rol", "Rol", "seleccion", fuente="roles"),
        ),
    },
    "lugares": {
        "titulo": "Lugares",
        "singular": "el lugar",
        "detalle": (
            "Sin escena del incidente nadie tuvo oportunidad: es el lugar "
            "sobre el que trabaja tuvo_oportunidad/2."
        ),
        "clave": ("nombre",),
        "columnas": (
            ("nombre", "Lugar", "nombre"),
            ("descripcion", "Descripción", "texto"),
            ("es_escena", "Escena", "si_no"),
            ("conectado_con", "Conectado con", "lista"),
        ),
        "campos": (
            campo("nombre", "Identificador", "atomo", clave=True),
            campo("descripcion", "Descripción", "texto"),
            campo("es_escena", "Es la escena del incidente", "casilla"),
            campo(
                "conectado_con",
                "Conectado con",
                "multiple",
                fuente="lugares",
                opcional=True,
            ),
        ),
    },
    "evidencias": {
        "titulo": "Evidencias",
        "singular": "la evidencia",
        "detalle": (
            "Solo huella, adn, video y registro ubican físicamente a alguien; "
            "son las que pueden contradecir una declaración."
        ),
        "clave": ("id",),
        "columnas": (
            ("id", "Id", "codigo"),
            ("tipo", "Tipo", "etiqueta"),
            ("lugar", "Lugar", "nombre"),
            ("hora", "Hora", "texto"),
            ("descripcion", "Descripción", "texto"),
            ("incrimina", "Incrimina a", "lista"),
        ),
        "campos": (
            campo("id", "Identificador", "atomo", clave=True, ayuda="e1, e2, ..."),
            campo("tipo", "Tipo", "seleccion", fuente="tipos_evidencia"),
            campo("lugar", "Lugar", "seleccion", fuente="lugares"),
            campo(
                "hora",
                "Hora",
                "hora_opcional",
                opcional=True,
                ayuda="0 a 23, o vacío si se desconoce",
            ),
            campo("descripcion", "Descripción", "texto"),
            campo(
                "incrimina",
                "Incrimina a",
                "multiple",
                fuente="personas",
                opcional=True,
            ),
        ),
    },
    "declaraciones": {
        "titulo": "Declaraciones",
        "singular": "la declaración",
        "detalle": (
            "El contenido tiene que ser uno de los términos que las reglas "
            "saben unificar; con cualquier otro, la declaración no "
            "contradiría nunca nada."
        ),
        "clave": ("id",),
        "columnas": (
            ("id", "Id", "codigo"),
            ("autor", "Autor", "nombre"),
            ("tipo", "Tipo", "etiqueta"),
            ("contenido", "Contenido", "codigo"),
        ),
        "campos": (
            campo("id", "Identificador", "atomo", clave=True, ayuda="d1, d2, ..."),
            campo("autor", "Autor", "seleccion", fuente="personas"),
            campo("tipo", "Tipo", "seleccion", fuente="tipos_declaracion"),
            campo("argumentos", "Argumentos", "argumentos"),
        ),
    },
    "relaciones": {
        "titulo": "Relaciones",
        "singular": "la relación",
        "detalle": (
            "Una relación conflictiva con la víctima —ex_pareja, deudor, "
            "rival o heredero— le deduce un motivo a quien la tiene."
        ),
        "clave": ("persona", "con_quien"),
        "columnas": (
            ("persona", "Persona", "nombre"),
            ("con_quien", "Con", "nombre"),
            ("tipo", "Tipo", "etiqueta"),
        ),
        "campos": (
            campo("persona", "Persona", "seleccion", fuente="personas", clave=True),
            campo("con_quien", "Con", "seleccion", fuente="personas", clave=True),
            campo("tipo", "Tipo", "seleccion", fuente="tipos_relacion"),
        ),
    },
    "coartadas": {
        "titulo": "Coartadas",
        "singular": "la coartada",
        "detalle": (
            "El respaldo decide si sirve: el testigo no puede ser sospechoso, "
            "la cámara tiene que estar en un lugar del caso y el documento "
            "tiene que ser una evidencia registrada."
        ),
        "clave": ("persona",),
        "columnas": (
            ("persona", "Persona", "nombre"),
            ("lugar", "Lugar", "nombre"),
            ("hora", "Hora", "texto"),
            ("respaldo", "Respaldo", "codigo"),
            ("veredicto", "Según el motor", "veredicto"),
        ),
        "campos": (
            campo("persona", "Persona", "seleccion", fuente="personas", clave=True),
            campo("lugar", "Lugar", "seleccion", fuente="lugares"),
            campo("hora", "Hora", "entero"),
            campo(
                "respaldo",
                "Tipo de respaldo",
                "seleccion",
                fuente="tipos_respaldo",
                valor_de="respaldo_tipo",
            ),
            campo(
                "respaldo_valor",
                "Respaldo",
                "referencia",
                opcional=True,
                ayuda="la persona, el lugar o la evidencia que lo respalda",
            ),
        ),
    },
    "motivos": {
        "titulo": "Motivos",
        "singular": "el motivo",
        "detalle": (
            "Solo los motivos declarados. Los que el motor deduce de una "
            "relación conflictiva no se listan acá: se quitan cambiando la "
            "relación."
        ),
        "clave": ("persona", "tipo"),
        "columnas": (
            ("persona", "Persona", "nombre"),
            ("tipo", "Motivo", "etiqueta"),
        ),
        "campos": (
            campo("persona", "Persona", "seleccion", fuente="personas", clave=True),
            campo("tipo", "Motivo", "seleccion", fuente="tipos_motivo", clave=True),
        ),
    },
    "oportunidades": {
        "titulo": "Oportunidades y medios",
        "singular": "el hecho",
        "detalle": (
            "Los cinco hechos con los que el motor deduce quién pudo estar en "
            "la escena y quién tenía con qué. No se editan: se dan de alta y "
            "de baja."
        ),
        "clave": ("tipo", "persona", "objeto", "hora"),
        "editable": False,
        "columnas": (
            ("tipo", "Hecho", "etiqueta"),
            ("persona", "Persona", "nombre"),
            ("objeto", "Lugar o medio", "nombre"),
            ("hora", "Hora", "texto"),
        ),
        "campos": (
            campo("tipo", "Hecho", "seleccion", fuente="tipos_oportunidad"),
            campo("persona", "Persona", "seleccion", fuente="personas"),
            campo(
                "objeto",
                "Lugar o medio",
                "referencia",
                ayuda="un lugar, o un medio si el hecho es posee_medio",
            ),
            campo(
                "hora",
                "Hora",
                "entero",
                opcional=True,
                ayuda="solo para visto_en y registro_acceso",
            ),
        ),
    },
}


#: `vio_a(bruno,salon,22)` -> funtor y argumentos, para volver a llenar el
#: formulario a partir del término que devuelve el backend.
TERMINO = re.compile(r"^([a-z][a-zA-Z0-9_]*)\((.*)\)$")


def partes_de_termino(termino: Any) -> tuple[str, list[str]]:
    """Separa un término en su funtor y sus argumentos.

    No es un lector de Prolog: los términos que llegan acá los arma el módulo
    administrativo, y en ellos ningún argumento lleva paréntesis ni comas.
    """
    crudo = str(termino or "").strip()
    coincide = TERMINO.match(crudo)
    if coincide is None:
        return crudo, []
    return coincide.group(1), [
        parte.strip() for parte in coincide.group(2).split(",") if parte.strip()
    ]


def desarmar_para_el_formulario(entidad: str, filas: list[dict[str, Any]]) -> None:
    """Desarma los términos que el backend entrega escritos.

    El contenido de una declaración y el respaldo de una coartada llegan como
    términos, que es lo correcto para mostrarlos; para editarlos hace falta el
    funtor por un lado y los argumentos por otro.
    """
    for fila in filas:
        if entidad == "declaraciones":
            _, fila["argumentos"] = partes_de_termino(fila.get("contenido"))
        elif entidad == "coartadas":
            clase, argumentos = partes_de_termino(fila.get("respaldo"))
            fila["respaldo_tipo"] = clase
            fila["respaldo_valor"] = argumentos[0] if argumentos else ""
        elif entidad == "evidencias" and fila.get("hora") == "desconocida":
            # El campo es numérico: "desconocida" se representa dejándolo vacío.
            fila["hora"] = ""


@app.template_global()
def clave_de(fila: dict[str, Any], claves: tuple[str, ...]) -> str:
    """Identidad de una fila. Va en la URL como `?editar=entidad:clave`."""
    return "|".join(str(fila.get(nombre) or "") for nombre in claves)


def entidad_valida(entidad: str) -> dict[str, Any]:
    """La especificación de la entidad, o 404 si la URL trae cualquier cosa."""
    if entidad not in ENTIDADES:
        abort(404)
    return ENTIDADES[entidad]


def valor_de_formulario(campo_spec: dict[str, Any], formulario: Any) -> Any:
    """Traduce lo que mandó el navegador al tipo que espera la API.

    El backend valida de nuevo todo esto; convertir acá evita mandarle
    `"hora": ""` cuando lo que se quiso decir fue "sin hora".
    """
    nombre = campo_spec["nombre"]
    tipo = campo_spec["tipo"]
    if tipo == "casilla":
        return nombre in formulario
    if tipo == "multiple":
        return formulario.getlist(nombre)
    if tipo == "argumentos":
        return [
            valor.strip() for valor in formulario.getlist("argumentos") if valor.strip()
        ]
    crudo = (formulario.get(nombre) or "").strip()
    if tipo == "hora_opcional":
        return crudo or "desconocida"
    if tipo == "entero":
        if not crudo:
            return None
        try:
            return int(crudo)
        except ValueError:
            # Se manda tal cual: el error del backend explica mejor que uno de acá.
            return crudo
    return crudo or None


def cuerpo_de_formulario(spec: dict[str, Any], formulario: Any, editar: bool) -> dict:
    """Arma el JSON de la petición desde la especificación de la entidad.

    Al editar se omiten los campos clave: van en la URL.
    """
    return {
        campo_spec["nombre"]: valor_de_formulario(campo_spec, formulario)
        for campo_spec in spec["campos"]
        if not (editar and campo_spec["clave"])
    }


def ruta_entidad(
    caso_id: str, entidad: str, clave: dict[str, Any] | None = None
) -> str:
    """Ruta del backend para la entidad, con o sin clave.

    Las oportunidades van por query string: `visto_en/3` no tiene identificador
    propio, lo identifica su contenido entero.
    """
    base = f"/api/admin/casos/{caso_id}/{entidad}"
    if not clave:
        return base
    if entidad == "oportunidades":
        partes = {k: v for k, v in clave.items() if v not in (None, "", "None")}
        return f"{base}?{urlencode(partes)}"
    return base + "".join(f"/{clave[nombre]}" for nombre in ENTIDADES[entidad]["clave"])


def clave_desde(spec: dict[str, Any], origen: Any) -> dict[str, Any]:
    """Extrae los campos que identifican un registro."""
    return {nombre: (origen.get(nombre) or "") for nombre in spec["clave"]}


@app.route("/admin")
def admin():
    """Tablero del módulo administrativo: avance de los casos y qué se cambió."""
    try:
        estado = api("/api/admin/estado")
        error = None
    except ErrorBackend as exc:
        estado, error = None, str(exc)
    return render_template(
        "admin.html",
        estado=estado,
        historial=api_opcional("/api/admin/historial", None),
        esquema=api_opcional("/api/admin/esquema", {}),
        investigaciones=resumen_de_investigaciones(),
        error=error,
    )


@app.route("/admin/casos", methods=["POST"])
def crear_caso():
    """Da de alta un caso con su propio módulo de Prolog."""
    cuerpo = {
        "id": (request.form.get("id") or "").strip(),
        "titulo": (request.form.get("titulo") or "").strip(),
        "descripcion": (request.form.get("descripcion") or "").strip(),
        "dificultad": (request.form.get("dificultad") or "media").strip(),
    }
    try:
        creado = api("/api/admin/casos", metodo="POST", json=cuerpo)
    except ErrorBackend as exc:
        flash(f"No se pudo crear el caso. {exc}", "error")
        return redirect(url_for("admin"))
    flash(
        f"Caso «{creado['titulo']}» creado. Ya usa las reglas de inferencia "
        "compartidas: cargale personas, lugares y hechos y la investigación "
        "empieza a deducir sobre él.",
        "exito",
    )
    return redirect(url_for("administrar_caso", caso_id=creado["id"]))


@app.route("/admin/casos/<caso_id>")
def administrar_caso(caso_id: str):
    """Editor de un caso: sus ocho entidades en una sola pantalla.

    `?editar=entidad:clave` abre una fila como formulario, sin JavaScript.
    """
    try:
        caso = api(f"/api/admin/casos/{caso_id}")
    except ErrorBackend as exc:
        if exc.codigo == 404:
            abort(404)
        flash(str(exc), "error")
        return redirect(url_for("admin"))

    datos = {
        entidad: api_opcional(ruta_entidad(caso_id, entidad), [])
        for entidad in ENTIDADES
    }
    for entidad, filas in datos.items():
        desarmar_para_el_formulario(entidad, filas)
    esquema = api_opcional("/api/admin/esquema", {})
    # Lo que depende del caso y no del esquema: así los desplegables solo
    # ofrecen personas, lugares y evidencias que existen.
    esquema["personas"] = [p["nombre"] for p in datos["personas"]]
    esquema["lugares"] = [lugar["nombre"] for lugar in datos["lugares"]]
    esquema["evidencias"] = [e["id"] for e in datos["evidencias"]]

    editar_entidad, _, editar_clave = (request.args.get("editar") or "").partition(":")
    return render_template(
        "admin_caso.html",
        caso=caso,
        entidades=ENTIDADES,
        datos=datos,
        esquema=esquema,
        editar_entidad=editar_entidad,
        editar_clave=editar_clave,
    )


@app.route("/admin/casos/<caso_id>/ficha", methods=["POST"])
def editar_ficha(caso_id: str):
    """Cambia la ficha del caso y los tres hechos que lo configuran."""
    try:
        api(
            f"/api/admin/casos/{caso_id}",
            metodo="PUT",
            json={
                "titulo": (request.form.get("titulo") or "").strip(),
                "descripcion": (request.form.get("descripcion") or "").strip(),
                "dificultad": (request.form.get("dificultad") or "media").strip(),
            },
        )
        escena = (request.form.get("escena") or "").strip()
        hora = (request.form.get("hora_incidente") or "").strip()
        api(
            f"/api/admin/casos/{caso_id}/ficha",
            metodo="PUT",
            json={
                "escena": escena or None,
                "hora_incidente": int(hora) if hora.isdigit() else None,
                "medios_requeridos": request.form.getlist("medios_requeridos"),
            },
        )
    except ErrorBackend as exc:
        flash(f"No se pudo guardar la ficha. {exc}", "error")
    else:
        flash("Ficha del caso actualizada.", "exito")
    return redirect(url_for("administrar_caso", caso_id=caso_id))


@app.route("/admin/casos/<caso_id>/eliminar", methods=["POST"])
def eliminar_caso(caso_id: str):
    try:
        resultado = api(f"/api/admin/casos/{caso_id}", metodo="DELETE")
    except ErrorBackend as exc:
        flash(f"No se pudo eliminar el caso. {exc}", "error")
    else:
        aclaracion = (
            "Se borró con todos sus hechos."
            if resultado.get("definitivo")
            else "Salió del catálogo; sus hechos siguen intactos y «restaurar» lo devuelve."
        )
        flash(f"Caso {caso_id} eliminado. {aclaracion}", "exito")
    return redirect(url_for("admin"))


@app.route("/admin/casos/<caso_id>/<entidad>/crear", methods=["POST"])
def crear_registro(caso_id: str, entidad: str):
    spec = entidad_valida(entidad)
    try:
        api(
            ruta_entidad(caso_id, entidad),
            metodo="POST",
            json=cuerpo_de_formulario(spec, request.form, editar=False),
        )
    except ErrorBackend as exc:
        flash(f"No se pudo agregar {spec['singular']}. {exc}", "error")
    else:
        flash(f"Se agregó {spec['singular']}.", "exito")
    return redirect(url_for("administrar_caso", caso_id=caso_id, _anchor=entidad))


@app.route("/admin/casos/<caso_id>/<entidad>/editar", methods=["POST"])
def editar_registro(caso_id: str, entidad: str):
    spec = entidad_valida(entidad)
    clave = clave_desde(spec, request.form)
    try:
        api(
            ruta_entidad(caso_id, entidad, clave),
            metodo="PUT",
            json=cuerpo_de_formulario(spec, request.form, editar=True),
        )
    except ErrorBackend as exc:
        flash(f"No se pudo modificar {spec['singular']}. {exc}", "error")
    else:
        flash(f"Se modificó {spec['singular']}.", "exito")
    return redirect(url_for("administrar_caso", caso_id=caso_id, _anchor=entidad))


@app.route("/admin/casos/<caso_id>/<entidad>/eliminar", methods=["POST"])
def eliminar_registro(caso_id: str, entidad: str):
    spec = entidad_valida(entidad)
    clave = clave_desde(spec, request.form)
    try:
        resultado = api(ruta_entidad(caso_id, entidad, clave), metodo="DELETE")
    except ErrorBackend as exc:
        flash(f"No se pudo eliminar {spec['singular']}. {exc}", "error")
    else:
        cascada = resultado.get("en_cascada") or {}
        arrastre = ", ".join(f"{cuantos} {que}" for que, cuantos in cascada.items())
        flash(
            f"Se eliminó {spec['singular']}."
            + (f" También se quitaron: {arrastre}." if arrastre else ""),
            "exito",
        )
    return redirect(url_for("administrar_caso", caso_id=caso_id, _anchor=entidad))


@app.route("/admin/restaurar", methods=["POST"])
def restaurar_administracion():
    """Deshace todos los cambios administrativos."""
    try:
        resultado = api("/api/admin/restaurar", metodo="POST")
    except ErrorBackend as exc:
        flash(f"No se pudo restaurar. {exc}", "error")
    else:
        flash(
            f"Se deshicieron {resultado['operaciones_deshechas']} operaciones. "
            "Los casos volvieron a su estado de fábrica.",
            "exito",
        )
    return redirect(url_for("admin"))


@app.route("/salud")
def salud():
    """Healthcheck del contenedor del frontend."""
    return {"estado": "ok", "backend": BACKEND_URL}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
