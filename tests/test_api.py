"""Pruebas de la API. Cada una atraviesa FastAPI -> PySwip -> Prolog."""

from __future__ import annotations

import pytest


def test_health_reporta_prolog_conectado(cliente):
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["prolog"] == "conectado"


def test_listar_casos_devuelve_los_cuatro(cliente):
    casos = cliente.get("/api/casos").json()
    assert {caso["id"] for caso in casos} == {"caso_demo", "caso1", "caso2", "caso3"}


def test_un_caso_inexistente_da_404(cliente):
    assert cliente.get("/api/casos/no_existe").status_code == 404


def test_los_sospechosos_traen_nivel_puntaje_e_indicios(cliente):
    """Un caso ya poblado devuelve su ranking con la forma que espera la interfaz."""
    respuesta = cliente.get("/api/casos/caso1/sospechosos")
    assert respuesta.status_code == 200
    sospechosos = respuesta.json()
    assert sospechosos, "caso1 ya tiene hechos: el ranking no puede venir vacío"
    for sospechoso in sospechosos:
        assert {"persona", "nivel_sospecha", "puntaje", "indicios"} <= set(sospechoso)


def test_sospechosos_vienen_ordenados_por_puntaje(cliente):
    sospechosos = cliente.get("/api/casos/caso_demo/sospechosos").json()
    puntajes = [s["puntaje"] for s in sospechosos]
    assert puntajes == sorted(puntajes, reverse=True)


def test_la_conclusion_incluye_las_reglas_activadas(cliente):
    conclusion = cliente.get("/api/casos/caso_demo/conclusion").json()
    assert conclusion["responsable"] == "bruno"
    reglas = [
        v["reglas_activadas"]
        for v in conclusion["veredictos"]
        if v["persona"] == "bruno"
    ][0]
    assert reglas, "la conclusión no trae la justificación"


def test_acusacion_correcta(cliente):
    respuesta = cliente.post(
        "/api/casos/caso_demo/acusacion", json={"sospechoso": "bruno"}
    )
    assert respuesta.json()["veredicto"] == "correcta"


def test_acusacion_incorrecta(cliente):
    respuesta = cliente.post(
        "/api/casos/caso_demo/acusacion", json={"sospechoso": "ana"}
    )
    assert respuesta.json()["veredicto"] == "incorrecta"


def test_acusar_a_alguien_que_no_es_del_caso_da_404(cliente):
    respuesta = cliente.post(
        "/api/casos/caso_demo/acusacion", json={"sospechoso": "fulano"}
    )
    assert respuesta.status_code == 404


@pytest.mark.parametrize(
    "malicioso",
    [
        "caso1), halt, foo(",
        "Variable",
        "caso1'",
        "caso1, halt",
    ],
)
def test_no_se_puede_inyectar_prolog_por_la_url(cliente, malicioso):
    """Las metas se arman concatenando texto, así que hay que validar."""
    respuesta = cliente.get(f"/api/casos/{malicioso}/sospechosos")
    assert respuesta.status_code in (400, 404)


def test_no_se_puede_inyectar_prolog_por_la_acusacion(cliente):
    respuesta = cliente.post(
        "/api/casos/caso_demo/acusacion", json={"sospechoso": "bruno), halt, foo("}
    )
    assert respuesta.status_code == 400


def test_admin_reporta_el_avance_contra_los_minimos(cliente):
    estado = cliente.get("/api/admin/estado").json()
    assert estado["minimos_por_caso"]["sospechosos"] == 4
    assert estado["minimos_por_caso"]["evidencias"] == 10
    assert estado["prolog"]["disponible"] is True
