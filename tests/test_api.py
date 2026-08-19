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


def test_solo_el_caso_de_referencia_viene_marcado_como_ejemplo(cliente):
    """caso_demo no cuenta entre los tres entregables y no alcanza los mínimos:
    el flag es lo que distingue eso de un caso a medio hacer."""
    casos = {caso["id"]: caso for caso in cliente.get("/api/casos").json()}
    assert casos["caso_demo"]["es_ejemplo"] is True
    assert casos["caso_demo"]["estado"] == "incompleto"
    for caso_id in ("caso1", "caso2", "caso3"):
        assert casos[caso_id]["es_ejemplo"] is False
        assert casos[caso_id]["estado"] == "completo"
    assert cliente.get("/api/casos/caso_demo").json()["es_ejemplo"] is True


def test_las_relaciones_marcan_las_conflictivas_y_a_la_victima(cliente):
    """El enunciado pide poder consultar las relaciones entre las personas."""
    relaciones = cliente.get("/api/casos/caso1/relaciones").json()
    assert relaciones, "caso1 declara relaciones entre sus personas"
    for relacion in relaciones:
        assert {
            "persona",
            "con_quien",
            "tipo",
            "es_conflictiva",
            "es_con_la_victima",
        } <= set(relacion)

    # heredero es conflictiva: es de donde el motor deduce un motivo.
    herederos = [r for r in relaciones if r["tipo"] == "heredero"]
    assert herederos, "caso1 tiene un heredero de la víctima"
    assert herederos[0]["es_conflictiva"]
    assert herederos[0]["es_con_la_victima"]


def test_las_oportunidades_no_repiten_a_una_persona(cliente):
    """`tuvo_oportunidad/2` tiene dos cláusulas: la fachada no debe duplicar filas."""
    oportunidades = cliente.get("/api/casos/caso_demo/oportunidades").json()
    pares = [(o["persona"], o["lugar"]) for o in oportunidades]
    assert pares, "caso_demo tiene personas con oportunidad"
    assert len(pares) == len(set(pares))


def test_el_responsable_tuvo_oportunidad(cliente):
    """Coherencia entre dos deducciones independientes del motor."""
    conclusion = cliente.get("/api/casos/caso1/conclusion").json()
    oportunidades = cliente.get("/api/casos/caso1/oportunidades").json()
    assert conclusion["responsable"] in [o["persona"] for o in oportunidades]


def test_admin_reporta_el_avance_contra_los_minimos(cliente):
    estado = cliente.get("/api/admin/estado").json()
    assert estado["minimos_por_caso"]["sospechosos"] == 4
    assert estado["minimos_por_caso"]["evidencias"] == 10
    assert estado["prolog"]["disponible"] is True


def test_admin_cuenta_las_reglas_de_inferencia_de_cada_caso(cliente):
    """Es el quinto mínimo del enunciado: sin la cuenta no se puede verificar."""
    estado = cliente.get("/api/admin/estado").json()
    minimo = estado["minimos_por_caso"]["reglas_de_inferencia"]
    assert minimo == 10

    reglas = {
        caso["id"]: caso["conteos"]["reglas_de_inferencia"] for caso in estado["casos"]
    }
    for caso_id in ("caso1", "caso2", "caso3"):
        assert reglas[caso_id] >= minimo, f"{caso_id} no llega a {minimo} reglas"
    # El de referencia no declara reglas propias: solo usa las compartidas.
    assert reglas["caso_demo"] == 0


def test_un_caso_sin_sus_reglas_propias_no_puede_estar_completo(motor):
    """Las reglas compartidas de reglas_base.pl no cuentan como propias, así que
    un caso que solo las use no alcanza el mínimo."""
    filas = motor.filas("estado_caso(caso_demo, Estado, _)")
    assert filas[0]["Estado"] == "incompleto"
    assert motor.filas("reglas_propias(caso_demo, N)")[0]["N"] == 0
