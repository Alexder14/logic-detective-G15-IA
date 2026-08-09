"""Pruebas de la interfaz web.

El backend se simula. Acá solo se prueba la capa de presentación —filtros,
rutas y plantillas—; la inferencia se prueba en test_prolog_integracion.py y la
API en test_api.py.
"""

from __future__ import annotations

import pytest


def caso(id_, dificultad, estado):
    return {
        "id": id_,
        "titulo": f"Caso {id_}",
        "descripcion": "Descripción de prueba.",
        "dificultad": dificultad,
        "estado": estado,
        "conteos": {
            "sospechosos": 4,
            "evidencias": 10,
            "lugares": 5,
            "declaraciones": 5,
        },
    }


CASOS = [
    caso("caso_demo", "facil", "incompleto"),
    caso("caso1", "media", "completo"),
    caso("caso2", "media", "pendiente"),
    caso("caso3", "dificil", "pendiente"),
]

# Los que el sorteo puede devolver: tienen hechos cargados.
INVESTIGABLES = {"caso_demo", "caso1"}


@pytest.fixture(autouse=True)
def backend_simulado(interfaz, monkeypatch):
    """Reemplaza las llamadas HTTP al backend por datos fijos."""

    def falso_api(ruta, metodo="GET", json=None):
        if ruta == "/api/casos":
            return list(CASOS)
        for c in CASOS:
            if ruta == f"/api/casos/{c['id']}":
                return c
        return []

    monkeypatch.setattr(interfaz, "api", falso_api)


# --------------------------------------------------------------------------
# Filtros (lógica pura)
# --------------------------------------------------------------------------


def test_sin_filtros_no_se_descarta_nada(interfaz):
    assert interfaz.filtrar_casos(CASOS, "", "") == CASOS


def test_filtrar_por_dificultad(interfaz):
    filtrados = interfaz.filtrar_casos(CASOS, "media", "")
    assert [c["id"] for c in filtrados] == ["caso1", "caso2"]


def test_filtrar_por_estado(interfaz):
    filtrados = interfaz.filtrar_casos(CASOS, "", "pendiente")
    assert [c["id"] for c in filtrados] == ["caso2", "caso3"]


def test_los_dos_filtros_se_combinan(interfaz):
    filtrados = interfaz.filtrar_casos(CASOS, "media", "completo")
    assert [c["id"] for c in filtrados] == ["caso1"]


@pytest.mark.parametrize("basura", ["", None, "MEDIANA", "'; drop", "facil2"])
def test_una_dificultad_invalida_se_ignora(interfaz, basura):
    """La URL la puede escribir el usuario: un valor raro no debe dar error."""
    assert interfaz.opcion(basura, interfaz.DIFICULTADES) == ""


def test_una_dificultad_valida_se_normaliza(interfaz):
    assert interfaz.opcion("  FACIL ", interfaz.DIFICULTADES) == "facil"


def test_los_conteos_cubren_todos_los_valores(interfaz):
    conteos = interfaz.contar_por(CASOS, "dificultad", interfaz.DIFICULTADES)
    assert conteos == {"facil": 1, "media": 2, "dificil": 1}


# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------


def test_el_listado_muestra_todos_los_casos(navegador):
    html = navegador.get("/investigacion").get_data(as_text=True)
    for c in CASOS:
        assert c["titulo"] in html


def test_el_listado_filtrado_oculta_los_demas(navegador):
    html = navegador.get("/investigacion?dificultad=dificil").get_data(as_text=True)
    assert "Caso caso3" in html
    assert "Caso caso1" not in html


def test_un_filtro_invalido_no_rompe_el_listado(navegador):
    respuesta = navegador.get("/investigacion?dificultad=inventada")
    assert respuesta.status_code == 200
    assert "Caso caso1" in respuesta.get_data(as_text=True)


def test_un_filtro_sin_resultados_avisa(navegador):
    html = navegador.get("/investigacion?dificultad=dificil&estado=completo")
    assert "Ningún caso coincide" in html.get_data(as_text=True)


def test_el_sorteo_manda_a_un_caso_con_hechos(navegador):
    """Nunca a uno 'pendiente': sería mandar al usuario a una página vacía."""
    for _ in range(15):
        respuesta = navegador.get("/investigacion/aleatorio")
        assert respuesta.status_code == 302
        assert respuesta.headers["Location"].split("/")[-1] in INVESTIGABLES


def test_el_sorteo_respeta_el_filtro(navegador):
    respuesta = navegador.get("/investigacion/aleatorio?dificultad=facil")
    assert respuesta.headers["Location"].endswith("/caso_demo")


def test_el_sorteo_sin_candidatos_vuelve_al_listado(navegador):
    """caso3 es difícil pero está pendiente, así que no hay a dónde mandar."""
    respuesta = navegador.get("/investigacion/aleatorio?dificultad=dificil")
    assert respuesta.status_code == 302
    assert "dificultad=dificil" in respuesta.headers["Location"]

    html = navegador.get(respuesta.headers["Location"]).get_data(as_text=True)
    assert "No hay casos con datos cargados" in html


def test_el_menu_marca_el_modulo_activo(navegador):
    html = navegador.get("/investigacion").get_data(as_text=True)
    assert 'aria-current="page"' in html


def test_la_pagina_de_inicio_responde(navegador):
    assert navegador.get("/").status_code == 200


def test_el_healthcheck_de_la_interfaz_responde(navegador):
    assert navegador.get("/salud").get_json()["estado"] == "ok"
