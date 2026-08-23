"""Pruebas del descubrimiento progresivo y la bitácora de investigación.

Cubre el flujo que exige el enunciado: el usuario no recibe toda la
información del caso de golpe, sino que la descubre con acciones (examinar
evidencia, interrogar una declaración, pedir una pista), y cada acción queda
registrada. Usa `caso_demo` porque es chico y estable (e1..e5, d1..d4).
"""

from __future__ import annotations


def crear_investigacion(cliente, caso_id="caso_demo") -> str:
    respuesta = cliente.post(f"/api/casos/{caso_id}/investigaciones")
    assert respuesta.status_code == 200
    return respuesta.json()["investigacion_id"]


def test_crear_investigacion_devuelve_id_y_puntaje_inicial(cliente):
    respuesta = cliente.post("/api/casos/caso_demo/investigaciones")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["caso_id"] == "caso_demo"
    assert cuerpo["puntaje"] == 100
    assert cuerpo["investigacion_id"]


def test_crear_investigacion_de_caso_inexistente_da_404(cliente):
    assert cliente.post("/api/casos/no_existe/investigaciones").status_code == 404


def test_evidencias_sin_investigacion_devuelve_todas(cliente):
    """Comportamiento previo intacto: sin investigacion_id no hay filtro."""
    evidencias = cliente.get("/api/casos/caso_demo/evidencias").json()
    assert len(evidencias) == 5


def test_evidencias_con_investigacion_arranca_vacio(cliente):
    inv_id = crear_investigacion(cliente)
    respuesta = cliente.get(
        "/api/casos/caso_demo/evidencias", params={"investigacion_id": inv_id}
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_examinar_evidencia_la_agrega_al_listado_y_a_la_bitacora(cliente):
    inv_id = crear_investigacion(cliente)
    respuesta = cliente.post(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/evidencias/e1/examinar"
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == "e1"
    assert cuerpo["incrimina"] == ["bruno"]

    evidencias = cliente.get(
        "/api/casos/caso_demo/evidencias", params={"investigacion_id": inv_id}
    ).json()
    assert [e["id"] for e in evidencias] == ["e1"]

    bitacora = cliente.get(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/bitacora"
    ).json()
    assert len(bitacora["acciones"]) == 1
    assert bitacora["acciones"][0]["tipo"] == "consultar"
    assert "e1" in bitacora["acciones"][0]["detalle"]


def test_examinar_evidencia_inexistente_da_404(cliente):
    inv_id = crear_investigacion(cliente)
    respuesta = cliente.post(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/evidencias/e99/examinar"
    )
    assert respuesta.status_code == 404


def test_declaraciones_con_investigacion_arranca_vacio_y_se_interroga_de_a_una(cliente):
    inv_id = crear_investigacion(cliente)
    vacio = cliente.get(
        "/api/casos/caso_demo/declaraciones", params={"investigacion_id": inv_id}
    ).json()
    assert vacio == []

    respuesta = cliente.post(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/declaraciones/d1/interrogar"
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["autor"] == "bruno"

    declaraciones = cliente.get(
        "/api/casos/caso_demo/declaraciones", params={"investigacion_id": inv_id}
    ).json()
    assert [d["id"] for d in declaraciones] == ["d1"]


def test_interrogar_declaracion_inexistente_da_404(cliente):
    inv_id = crear_investigacion(cliente)
    respuesta = cliente.post(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/declaraciones/d99/interrogar"
    )
    assert respuesta.status_code == 404


def test_pedir_pista_descuenta_puntaje_y_no_repite(cliente):
    inv_id = crear_investigacion(cliente)
    todas = cliente.get("/api/casos/caso_demo/pistas").json()
    assert todas, "caso_demo debería producir al menos una pista"

    vistas = set()
    puntaje_anterior = 100
    for _ in range(len(set(todas))):
        respuesta = cliente.post(
            f"/api/casos/caso_demo/investigaciones/{inv_id}/pistas/siguiente"
        )
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["pista"] not in vistas, "no debe repetir una pista ya dada"
        vistas.add(cuerpo["pista"])
        assert cuerpo["puntaje"] == max(0, puntaje_anterior - 5)
        puntaje_anterior = cuerpo["puntaje"]

    agotada = cliente.post(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/pistas/siguiente"
    )
    assert agotada.status_code == 404


def test_bitacora_acumula_acciones_de_distintos_tipos(cliente):
    inv_id = crear_investigacion(cliente)
    cliente.get("/api/casos/caso_demo/sospechosos", params={"investigacion_id": inv_id})
    cliente.get(
        "/api/casos/caso_demo/contradicciones", params={"investigacion_id": inv_id}
    )
    cliente.post(f"/api/casos/caso_demo/investigaciones/{inv_id}/pistas/siguiente")

    bitacora = cliente.get(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/bitacora"
    ).json()
    tipos = [accion["tipo"] for accion in bitacora["acciones"]]
    assert tipos == ["consultar", "deducir", "pedir_ayuda"]


def test_investigacion_de_otro_caso_da_404(cliente):
    inv_id = crear_investigacion(cliente, caso_id="caso_demo")
    respuesta = cliente.get(
        "/api/casos/caso1/evidencias", params={"investigacion_id": inv_id}
    )
    assert respuesta.status_code == 404


def test_investigacion_inexistente_da_404(cliente):
    respuesta = cliente.get("/api/casos/caso_demo/investigaciones/no-existe/bitacora")
    assert respuesta.status_code == 404


def test_acusacion_con_investigacion_queda_en_la_bitacora(cliente):
    inv_id = crear_investigacion(cliente)
    respuesta = cliente.post(
        "/api/casos/caso_demo/acusacion",
        json={"sospechoso": "bruno", "investigacion_id": inv_id},
    )
    assert respuesta.status_code == 200

    bitacora = cliente.get(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/bitacora"
    ).json()
    assert bitacora["acciones"][-1]["tipo"] == "acusar"
    assert "bruno" in bitacora["acciones"][-1]["detalle"]


def test_acusacion_sin_investigacion_no_falla(cliente):
    """El parámetro es opcional: acusar sin investigación sigue funcionando."""
    respuesta = cliente.post(
        "/api/casos/caso_demo/acusacion", json={"sospechoso": "bruno"}
    )
    assert respuesta.status_code == 200


def test_informe_final_incluye_avance_bitacora_y_conclusion(cliente):
    inv_id = crear_investigacion(cliente)
    cliente.post(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/evidencias/e1/examinar"
    )
    cliente.post(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/declaraciones/d1/interrogar"
    )
    cliente.post(f"/api/casos/caso_demo/investigaciones/{inv_id}/pistas/siguiente")

    informe = cliente.get(
        f"/api/casos/caso_demo/investigaciones/{inv_id}/informe"
    ).json()

    assert informe["avance"]["evidencias_examinadas"] == 1
    assert informe["avance"]["evidencias_totales"] == 5
    assert informe["avance"]["declaraciones_interrogadas"] == 1
    assert informe["avance"]["declaraciones_totales"] == 4
    assert informe["avance"]["pistas_usadas"] == 1
    assert informe["puntaje_final"] == 95
    assert len(informe["bitacora"]) == 3
    assert informe["conclusion"]["responsable"] == "bruno"


def test_filtro_de_casos_por_dificultad(cliente):
    faciles = cliente.get("/api/casos", params={"dificultad": "facil"}).json()
    assert faciles, "caso_demo es facil"
    assert all(c["dificultad"] == "facil" for c in faciles)


def test_filtro_de_casos_por_estado(cliente):
    completos = cliente.get("/api/casos", params={"estado": "completo"}).json()
    assert {"caso1", "caso2", "caso3"} <= {c["id"] for c in completos}
    assert all(c["estado"] == "completo" for c in completos)


def test_filtro_de_casos_combinado_sin_resultados(cliente):
    vacio = cliente.get(
        "/api/casos", params={"dificultad": "dificil", "estado": "pendiente"}
    ).json()
    assert vacio == []
