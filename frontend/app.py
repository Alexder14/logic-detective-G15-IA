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
    """Listado de casos para iniciar una investigación."""
    try:
        casos = api("/api/casos")
        error = None
    except ErrorBackend as exc:
        casos, error = [], str(exc)
    return render_template("investigacion.html", casos=casos, error=error)


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
