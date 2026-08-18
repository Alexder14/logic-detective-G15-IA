"""Interfaz web de Logic Detective.

Dos módulos, como pide el enunciado:

  /investigacion   resolver casos
  /admin           estado de los casos

Este servidor no razona ni guarda estado: todo lo pide al backend, que lo
consulta a Prolog. Si te ves calculando algo acá, va en Prolog.

Levantar en desarrollo:
    BACKEND_URL=http://localhost:8000 python frontend/app.py
"""

from __future__ import annotations

import os
import random
from typing import Any

import requests
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)

# Solo para los mensajes flash. En el despliegue hay que pasar SECRET_KEY por
# variable de entorno.
app.secret_key = os.environ.get("SECRET_KEY", "logic-detective-dev")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 10


class ErrorBackend(Exception):
    """El backend no respondió o respondió con error."""


def api(ruta: str, metodo: str = "GET", json: dict | None = None) -> Any:
    """Llama al backend y devuelve el JSON.

    Centraliza el manejo de errores para que, si el backend o Prolog están
    caídos, la interfaz muestre un mensaje y no una traza.
    """
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
        raise ErrorBackend(f"{respuesta.status_code}: {detalle}")
    return respuesta.json()


def api_opcional(ruta: str, por_defecto: Any) -> Any:
    """Como api() pero devuelve un valor por defecto en lugar de fallar.

    Para las secciones de la vista de caso: que falte una no debería tumbar la
    página entera.
    """
    try:
        return api(ruta)
    except ErrorBackend:
        return por_defecto


# --------------------------------------------------------------------------
# Filtros del listado de casos
# --------------------------------------------------------------------------
#
# El filtro se resuelve acá, sobre la lista que ya devolvió el backend. No es
# inferencia, es presentación: decide qué filas se dibujan, no qué es verdad.
# Cuando el backend acepte ?dificultad= y ?estado= en /api/casos (está como
# TODO(backend) en main.py) esto se cambia por pasarle los parámetros y borrar
# filtrar_casos().

DIFICULTADES = ("facil", "media", "dificil")
ESTADOS = ("completo", "incompleto", "pendiente")

ETIQUETAS_DIFICULTAD = {"facil": "Fácil", "media": "Media", "dificil": "Difícil"}
ETIQUETAS_ESTADO = {
    "completo": "Completo",
    "incompleto": "Incompleto",
    "pendiente": "Pendiente",
}


def opcion(valor: str | None, permitidos: tuple[str, ...]) -> str:
    """Normaliza un parámetro de la URL. Devuelve "" si no es uno esperado."""
    valor = (valor or "").strip().lower()
    return valor if valor in permitidos else ""


def filtrar_casos(
    casos: list[dict[str, Any]], dificultad: str, estado: str
) -> list[dict[str, Any]]:
    """Aplica los filtros activos. Un filtro vacío no descarta nada."""
    return [
        caso
        for caso in casos
        if (not dificultad or caso.get("dificultad") == dificultad)
        and (not estado or caso.get("estado") == estado)
    ]


def contar_por(
    casos: list[dict[str, Any]], campo: str, valores: tuple[str, ...]
) -> dict[str, int]:
    """Cuántos casos hay de cada valor, para el contador de cada filtro."""
    return {v: sum(1 for caso in casos if caso.get(campo) == v) for v in valores}


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
    pendiente. Un valor que no exista se ignora en lugar de dar error: la URL
    la puede escribir el usuario a mano.
    """
    dificultad = opcion(request.args.get("dificultad"), DIFICULTADES)
    estado = opcion(request.args.get("estado"), ESTADOS)
    try:
        casos = api("/api/casos")
        error = None
    except ErrorBackend as exc:
        casos, error = [], str(exc)
    return render_template(
        "investigacion.html",
        casos=filtrar_casos(casos, dificultad, estado),
        total=len(casos),
        dificultad=dificultad,
        estado=estado,
        dificultades=DIFICULTADES,
        estados=ESTADOS,
        etiquetas_dificultad=ETIQUETAS_DIFICULTAD,
        etiquetas_estado=ETIQUETAS_ESTADO,
        conteos_dificultad=contar_por(casos, "dificultad", DIFICULTADES),
        conteos_estado=contar_por(casos, "estado", ESTADOS),
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
        casos = api("/api/casos")
    except ErrorBackend as exc:
        flash(f"No se pudo obtener la lista de casos. {exc}", "error")
        return redirect(volver)

    candidatos = [
        caso
        for caso in filtrar_casos(casos, dificultad, estado)
        if caso.get("estado") != "pendiente"
    ]
    if not candidatos:
        flash("No hay casos con datos cargados que coincidan con el filtro.", "error")
        return redirect(volver)
    return redirect(url_for("investigar_caso", caso_id=random.choice(candidatos)["id"]))


@app.route("/investigacion/<caso_id>")
def investigar_caso(caso_id: str):
    """Vista de trabajo del detective sobre un caso.

    TODO(interfaz): por ahora muestra todo junto. Falta el flujo de acciones de
    investigación y la bitácora.
    """
    try:
        caso = api(f"/api/casos/{caso_id}")
    except ErrorBackend as exc:
        return render_template("caso.html", caso=None, error=str(exc)), 404

    return render_template(
        "caso.html",
        caso=caso,
        error=None,
        sospechosos=api_opcional(f"/api/casos/{caso_id}/sospechosos", []),
        evidencias=api_opcional(f"/api/casos/{caso_id}/evidencias", []),
        lugares=api_opcional(f"/api/casos/{caso_id}/lugares", []),
        declaraciones=api_opcional(f"/api/casos/{caso_id}/declaraciones", []),
        coartadas=api_opcional(f"/api/casos/{caso_id}/coartadas", []),
        motivos=api_opcional(f"/api/casos/{caso_id}/motivos", []),
        contradicciones=api_opcional(f"/api/casos/{caso_id}/contradicciones", []),
        linea_temporal=api_opcional(f"/api/casos/{caso_id}/linea-temporal", []),
        pistas=api_opcional(f"/api/casos/{caso_id}/pistas", []),
        conclusion=api_opcional(f"/api/casos/{caso_id}/conclusion", None),
        resultado=None,
    )


@app.route("/investigacion/<caso_id>/acusacion", methods=["POST"])
def acusar(caso_id: str):
    """Emite la acusación final contra un sospechoso."""
    sospechoso = (request.form.get("sospechoso") or "").strip()
    if not sospechoso:
        flash("Elegí a un sospechoso antes de acusar.", "error")
        return redirect(url_for("investigar_caso", caso_id=caso_id))
    try:
        resultado = api(
            f"/api/casos/{caso_id}/acusacion",
            metodo="POST",
            json={"sospechoso": sospechoso},
        )
        flash(f"Acusación {resultado['veredicto']}.", resultado["veredicto"])
    except ErrorBackend as exc:
        flash(f"No se pudo evaluar la acusación. {exc}", "error")
    return redirect(url_for("investigar_caso", caso_id=caso_id))


# --------------------------------------------------------------------------
# Módulo administrativo
# --------------------------------------------------------------------------


@app.route("/admin")
def admin():
    """Estado de los casos frente a los mínimos que exige el enunciado."""
    try:
        estado = api("/api/admin/estado")
        error = None
    except ErrorBackend as exc:
        estado, error = None, str(exc)
    return render_template("admin.html", estado=estado, error=error)


@app.route("/salud")
def salud():
    """Healthcheck del contenedor del frontend."""
    return {"estado": "ok", "backend": BACKEND_URL}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
