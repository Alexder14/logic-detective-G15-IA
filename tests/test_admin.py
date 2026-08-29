"""Pruebas del módulo administrativo.

Atraviesan la pila entera hasta Prolog, sin dobles: lo que hay que comprobar es
que un `assertz` sobre un módulo ya cargado se vea en la deducción siguiente.

El motor es de sesión y lo comparten todas las pruebas del proyecto, así que
cada una deshace lo suyo con la fixture `base_limpia`.
"""

from __future__ import annotations

import json

import pytest

from app.terminos import ValorInvalido, atomo, hecho, hora, texto, uno_de


@pytest.fixture
def base_limpia(cliente):
    """Deja la base de conocimiento como estaba, pase lo que pase en la prueba."""
    yield cliente
    cliente.post("/api/admin/restaurar")


# --------------------------------------------------------------------------
# terminos.py
# --------------------------------------------------------------------------


def test_un_atomo_valido_pasa_tal_cual():
    assert atomo("victor_cordero", "nombre") == "victor_cordero"


@pytest.mark.parametrize(
    "valor",
    [
        "Mayuscula",
        "con espacio",
        "acentué",
        "",
        "1numero",
        "caso1), halt, foo(",
        "x" * 65,
    ],
)
def test_lo_que_no_es_un_atomo_se_rechaza(valor):
    """Ninguno de estos puede llegar a interpolarse en una meta de Prolog."""
    with pytest.raises(ValorInvalido):
        atomo(valor, "nombre")


def test_el_texto_se_cita_y_se_escapa():
    """La comilla se duplica, igual que como escribe SWI-Prolog: así el término
    se puede volver a leer, que es de lo que depende deshacer una baja."""
    assert texto("Con 'comilla'", "descripcion") == "'Con ''comilla'''"
    assert texto("Barra \\ invertida", "descripcion") == "'Barra \\\\ invertida'"


def test_el_texto_normaliza_espacios_y_exige_contenido():
    assert texto("  dos   espacios  ", "descripcion") == "'dos espacios'"
    with pytest.raises(ValorInvalido):
        texto("   ", "descripcion")


def test_la_hora_acepta_el_rango_del_dia_y_nada_mas():
    assert hora(0, "hora") == "0"
    assert hora(23, "hora") == "23"
    with pytest.raises(ValorInvalido):
        hora(24, "hora")
    with pytest.raises(ValorInvalido):
        hora("tarde", "hora")


def test_desconocida_solo_donde_el_esquema_la_admite():
    assert hora("desconocida", "hora", permite_desconocida=True) == "desconocida"
    with pytest.raises(ValorInvalido):
        hora("desconocida", "hora")


def test_uno_de_rechaza_lo_que_no_esta_en_el_vocabulario():
    assert uno_de("media", "dificultad", ("facil", "media")) == "media"
    with pytest.raises(ValorInvalido):
        uno_de("imposible", "dificultad", ("facil", "media"))


def test_hecho_arma_el_termino():
    assert hecho("motivo", "ana", "deuda") == "motivo(ana,deuda)"
    assert hecho("ninguno") == "ninguno"


# --------------------------------------------------------------------------
# Esquema
# --------------------------------------------------------------------------


def test_el_esquema_publica_el_vocabulario_que_usa_la_interfaz(cliente):
    esquema = cliente.get("/api/admin/esquema").json()
    assert "media" in esquema["dificultades"]
    assert "sospechoso" in esquema["roles"]
    assert "huella" in esquema["tipos_evidencia"]
    assert esquema["tipos_declaracion"]["estuvo_en"] == ["persona", "lugar", "hora"]
    assert esquema["tipos_oportunidad"]["visto_en"]["hora"] is True
    assert esquema["tipos_oportunidad"]["posee_medio"]["hora"] is False


# --------------------------------------------------------------------------
# CRUD de personas
# --------------------------------------------------------------------------


def test_crud_completo_de_una_persona(base_limpia):
    cliente = base_limpia

    alta = cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "testigo"},
    )
    assert alta.status_code == 201

    personas = cliente.get("/api/admin/casos/caso1/personas").json()
    assert {"nombre": "nadia_luna", "rol": "testigo"} in personas

    cambio = cliente.put(
        "/api/admin/casos/caso1/personas/nadia_luna", json={"rol": "sospechoso"}
    )
    assert cambio.status_code == 200
    personas = cliente.get("/api/admin/casos/caso1/personas").json()
    assert {"nombre": "nadia_luna", "rol": "sospechoso"} in personas
    assert {"nombre": "nadia_luna", "rol": "testigo"} not in personas

    baja = cliente.delete("/api/admin/casos/caso1/personas/nadia_luna")
    assert baja.status_code == 200
    nombres = [
        p["nombre"] for p in cliente.get("/api/admin/casos/caso1/personas").json()
    ]
    assert "nadia_luna" not in nombres


def test_no_se_puede_repetir_una_persona(base_limpia):
    cliente = base_limpia
    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "testigo"},
    )
    repetida = cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "sospechoso"},
    )
    assert repetida.status_code == 400
    assert repetida.json()["campo"] == "nombre"


def test_borrar_una_persona_se_lleva_lo_que_colgaba_de_ella(base_limpia):
    """Una relación de alguien que ya no está no es un dato incompleto sino
    falso: el motor deduciría con él."""
    cliente = base_limpia
    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "sospechoso"},
    )
    cliente.post(
        "/api/admin/casos/caso1/motivos",
        json={"persona": "nadia_luna", "tipo": "venganza"},
    )
    cliente.post(
        "/api/admin/casos/caso1/relaciones",
        json={
            "persona": "nadia_luna",
            "con_quien": "adriana_belmonte",
            "tipo": "rival",
        },
    )

    baja = cliente.delete("/api/admin/casos/caso1/personas/nadia_luna").json()
    assert baja["en_cascada"]["motivo"] == 1
    assert baja["en_cascada"]["relacion"] == 1

    motivos = cliente.get("/api/admin/casos/caso1/motivos").json()
    assert all(m["persona"] != "nadia_luna" for m in motivos)


# --------------------------------------------------------------------------
# CRUD del resto de las entidades
# --------------------------------------------------------------------------


def test_crud_de_una_evidencia_con_incriminados(base_limpia):
    cliente = base_limpia
    alta = cliente.post(
        "/api/admin/casos/caso1/evidencias",
        json={
            "id": "e91",
            "tipo": "video",
            "lugar": "salon_principal",
            "hora": 22,
            "descripcion": "Cámara del acceso lateral",
            "incrimina": ["hugo_paredes"],
        },
    )
    assert alta.status_code == 201

    registrada = next(
        e
        for e in cliente.get("/api/admin/casos/caso1/evidencias").json()
        if e["id"] == "e91"
    )
    assert registrada["incrimina"] == ["hugo_paredes"]

    cliente.put(
        "/api/admin/casos/caso1/evidencias/e91",
        json={
            "tipo": "huella",
            "lugar": "guardarropa",
            "hora": "desconocida",
            "descripcion": "Huella parcial en la puerta",
            "incrimina": ["isabela_duarte"],
        },
    )
    modificada = next(
        e
        for e in cliente.get("/api/admin/casos/caso1/evidencias").json()
        if e["id"] == "e91"
    )
    assert modificada["tipo"] == "huella"
    assert modificada["hora"] == "desconocida"
    assert modificada["incrimina"] == ["isabela_duarte"]

    assert cliente.delete("/api/admin/casos/caso1/evidencias/e91").status_code == 200


def test_crud_de_un_lugar_con_conexiones(base_limpia):
    cliente = base_limpia
    alta = cliente.post(
        "/api/admin/casos/caso1/lugares",
        json={
            "nombre": "terraza",
            "descripcion": "Terraza exterior del salón",
            "conectado_con": ["salon_principal"],
        },
    )
    assert alta.status_code == 201
    registrado = next(
        lugar
        for lugar in cliente.get("/api/admin/casos/caso1/lugares").json()
        if lugar["nombre"] == "terraza"
    )
    assert registrado["conectado_con"] == ["salon_principal"]
    assert registrado["es_escena"] is False

    assert cliente.delete("/api/admin/casos/caso1/lugares/terraza").status_code == 200


def test_un_lugar_no_se_conecta_consigo_mismo(base_limpia):
    respuesta = base_limpia.post(
        "/api/admin/casos/caso1/lugares",
        json={
            "nombre": "terraza",
            "descripcion": "Terraza",
            "conectado_con": ["terraza"],
        },
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["campo"] == "conectado_con"


def test_crud_de_una_declaracion(base_limpia):
    cliente = base_limpia
    alta = cliente.post(
        "/api/admin/casos/caso1/declaraciones",
        json={
            "id": "d91",
            "autor": "camila_rios",
            "tipo": "vio_a",
            "argumentos": ["hugo_paredes", "cocina_catering", 22],
        },
    )
    assert alta.status_code == 201
    assert alta.json()["contenido"] == "vio_a(hugo_paredes,cocina_catering,22)"

    cambio = cliente.put(
        "/api/admin/casos/caso1/declaraciones/d91",
        json={
            "autor": "camila_rios",
            "tipo": "no_estuvo_en",
            "argumentos": ["hugo_paredes", "cocina_catering", 22],
        },
    )
    assert cambio.json()["contenido"] == "no_estuvo_en(hugo_paredes,cocina_catering,22)"
    assert cliente.delete("/api/admin/casos/caso1/declaraciones/d91").status_code == 200


def test_una_declaracion_con_la_cantidad_de_argumentos_equivocada_se_rechaza(
    base_limpia,
):
    respuesta = base_limpia.post(
        "/api/admin/casos/caso1/declaraciones",
        json={
            "id": "d92",
            "autor": "camila_rios",
            "tipo": "posee",
            "argumentos": ["hugo_paredes", "llave", 22],
        },
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["campo"] == "argumentos"


def test_crud_de_una_coartada_y_su_respaldo(base_limpia):
    cliente = base_limpia
    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "sospechoso"},
    )
    alta = cliente.post(
        "/api/admin/casos/caso1/coartadas",
        json={
            "persona": "nadia_luna",
            "lugar": "guardarropa",
            "hora": 22,
            "respaldo": "testigo",
            "respaldo_valor": "camila_rios",
        },
    )
    assert alta.status_code == 201
    assert alta.json()["respaldo"] == "testigo(camila_rios)"

    registrada = next(
        c
        for c in cliente.get("/api/admin/casos/caso1/coartadas").json()
        if c["persona"] == "nadia_luna"
    )
    assert registrada["veredicto"]["estado"] == "valida"

    assert (
        cliente.delete("/api/admin/casos/caso1/coartadas/nadia_luna").status_code == 200
    )


def test_un_respaldo_necesita_su_argumento(base_limpia):
    cliente = base_limpia
    # Los cuatro sospechosos del caso 1 ya tienen coartada: el alta fallaría
    # antes de llegar a mirar el respaldo.
    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "sospechoso"},
    )
    respuesta = cliente.post(
        "/api/admin/casos/caso1/coartadas",
        json={
            "persona": "nadia_luna",
            "lugar": "guardarropa",
            "hora": 22,
            "respaldo": "documento",
        },
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["campo"] == "respaldo_valor"


def test_una_persona_no_puede_tener_dos_coartadas(base_limpia):
    respuesta = base_limpia.post(
        "/api/admin/casos/caso1/coartadas",
        json={
            "persona": "hugo_paredes",
            "lugar": "guardarropa",
            "hora": 22,
            "respaldo": "ninguno",
        },
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["campo"] == "persona"


def test_crud_de_relaciones_y_motivos(base_limpia):
    cliente = base_limpia
    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "sospechoso"},
    )
    assert (
        cliente.post(
            "/api/admin/casos/caso1/relaciones",
            json={
                "persona": "nadia_luna",
                "con_quien": "victor_cordero",
                "tipo": "socio",
            },
        ).status_code
        == 201
    )
    cambio = cliente.put(
        "/api/admin/casos/caso1/relaciones/nadia_luna/victor_cordero",
        json={"tipo": "deudor"},
    )
    assert cambio.json()["tipo"] == "deudor"

    assert (
        cliente.post(
            "/api/admin/casos/caso1/motivos",
            json={"persona": "nadia_luna", "tipo": "deuda"},
        ).status_code
        == 201
    )
    cambio = cliente.put(
        "/api/admin/casos/caso1/motivos/nadia_luna/deuda", json={"tipo": "herencia"}
    )
    assert cambio.json()["tipo"] == "herencia"
    assert (
        cliente.delete("/api/admin/casos/caso1/motivos/nadia_luna/herencia").status_code
        == 200
    )


def test_una_relacion_con_uno_mismo_se_rechaza(base_limpia):
    respuesta = base_limpia.post(
        "/api/admin/casos/caso1/relaciones",
        json={
            "persona": "hugo_paredes",
            "con_quien": "hugo_paredes",
            "tipo": "socio",
        },
    )
    assert respuesta.status_code == 400


def test_alta_y_baja_de_oportunidades(base_limpia):
    cliente = base_limpia
    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "sospechoso"},
    )
    assert (
        cliente.post(
            "/api/admin/casos/caso1/oportunidades",
            json={
                "tipo": "visto_en",
                "persona": "nadia_luna",
                "objeto": "salon_principal",
                "hora": 22,
            },
        ).status_code
        == 201
    )
    assert (
        cliente.post(
            "/api/admin/casos/caso1/oportunidades",
            json={
                "tipo": "posee_medio",
                "persona": "nadia_luna",
                "objeto": "llave",
            },
        ).status_code
        == 201
    )
    baja = cliente.delete(
        "/api/admin/casos/caso1/oportunidades",
        params={
            "tipo": "visto_en",
            "persona": "nadia_luna",
            "objeto": "salon_principal",
            "hora": 22,
        },
    )
    assert baja.status_code == 200


def test_visto_en_exige_hora_y_posee_medio_exige_un_medio(base_limpia):
    cliente = base_limpia
    sin_hora = cliente.post(
        "/api/admin/casos/caso1/oportunidades",
        json={
            "tipo": "visto_en",
            "persona": "hugo_paredes",
            "objeto": "salon_principal",
        },
    )
    assert sin_hora.status_code == 400
    assert sin_hora.json()["campo"] == "hora"

    medio_inventado = cliente.post(
        "/api/admin/casos/caso1/oportunidades",
        json={
            "tipo": "posee_medio",
            "persona": "hugo_paredes",
            "objeto": "salon_principal",
        },
    )
    assert medio_inventado.status_code == 400


# --------------------------------------------------------------------------
# Validaciones
# --------------------------------------------------------------------------


def test_no_se_puede_inyectar_prolog_por_un_campo(base_limpia):
    """Sin validar, esto se ejecutaría como código Prolog."""
    respuesta = base_limpia.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "x), halt, sospechoso(y", "rol": "testigo"},
    )
    assert respuesta.status_code == 400
    assert base_limpia.get("/health").status_code == 200


def test_no_se_puede_referir_a_alguien_que_no_esta_en_el_caso(base_limpia):
    respuesta = base_limpia.post(
        "/api/admin/casos/caso1/motivos",
        json={"persona": "fantasma", "tipo": "deuda"},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["campo"] == "persona"


def test_una_evidencia_no_puede_apuntar_a_un_lugar_inexistente(base_limpia):
    respuesta = base_limpia.post(
        "/api/admin/casos/caso1/evidencias",
        json={
            "id": "e93",
            "tipo": "huella",
            "lugar": "sotano_inventado",
            "descripcion": "x",
        },
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["campo"] == "lugar"


def test_una_evidencia_invalida_no_deja_nada_a_medio_escribir(base_limpia):
    """Se valida todo antes de escribir nada."""
    cliente = base_limpia
    antes = len(cliente.get("/api/admin/casos/caso1/evidencias").json())
    respuesta = cliente.post(
        "/api/admin/casos/caso1/evidencias",
        json={
            "id": "e94",
            "tipo": "huella",
            "lugar": "salon_principal",
            "descripcion": "x",
            "incrimina": ["hugo_paredes", "fantasma"],
        },
    )
    assert respuesta.status_code == 400
    assert len(cliente.get("/api/admin/casos/caso1/evidencias").json()) == antes


def test_modificar_algo_que_no_existe_da_404(base_limpia):
    assert (
        base_limpia.put(
            "/api/admin/casos/caso1/evidencias/no_existe",
            json={
                "tipo": "huella",
                "lugar": "salon_principal",
                "descripcion": "x",
            },
        ).status_code
        == 404
    )


def test_administrar_un_caso_inexistente_da_404(cliente):
    assert cliente.get("/api/admin/casos/no_existe/personas").status_code == 404


# --------------------------------------------------------------------------
# Integración con el módulo de investigación
# --------------------------------------------------------------------------


def test_un_sospechoso_creado_en_administracion_entra_a_la_deduccion(base_limpia):
    """El punto del módulo: se edita la misma base que consulta el motor."""
    cliente = base_limpia
    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "sospechoso"},
    )
    cliente.post(
        "/api/admin/casos/caso1/motivos",
        json={"persona": "nadia_luna", "tipo": "venganza"},
    )
    cliente.post(
        "/api/admin/casos/caso1/oportunidades",
        json={
            "tipo": "visto_en",
            "persona": "nadia_luna",
            "objeto": "salon_principal",
            "hora": 22,
        },
    )

    ranking = cliente.get("/api/casos/caso1/sospechosos").json()
    nadia = next(s for s in ranking if s["persona"] == "nadia_luna")
    assert nadia["puntaje"] > 0
    assert "motivo" in nadia["indicios"]
    assert "oportunidad" in nadia["indicios"]

    # Y la explicación cita las reglas que se activaron por esos hechos.
    conclusion = cliente.get("/api/casos/caso1/conclusion").json()
    veredicto = next(
        v for v in conclusion["veredictos"] if v["persona"] == "nadia_luna"
    )
    reglas = {regla["regla"] for regla in veredicto["reglas_activadas"]}
    assert {"tiene_motivo", "tuvo_oportunidad"} <= reglas


def test_borrar_las_evidencias_de_alguien_le_quita_ese_indicio(base_limpia):
    """Lo que administración borra deja de pesar.

    Se borran todas las que lo incriminan porque el indicio `evidencia_directa`
    lo sostiene cualquiera de ellas.
    """
    cliente = base_limpia
    victor = next(
        s
        for s in cliente.get("/api/casos/caso1/sospechosos").json()
        if s["persona"] == "victor_cordero"
    )
    assert "evidencia_directa" in victor["indicios"]

    for evidencia in cliente.get("/api/admin/casos/caso1/evidencias").json():
        if "victor_cordero" in evidencia["incrimina"]:
            baja = cliente.delete(
                f"/api/admin/casos/caso1/evidencias/{evidencia['id']}"
            )
            assert baja.status_code == 200

    despues = next(
        s
        for s in cliente.get("/api/casos/caso1/sospechosos").json()
        if s["persona"] == "victor_cordero"
    )
    assert "evidencia_directa" not in despues["indicios"]
    assert despues["puntaje"] < victor["puntaje"]


# --------------------------------------------------------------------------
# Casos
# --------------------------------------------------------------------------


def test_un_caso_creado_desde_administracion_hereda_las_reglas(base_limpia):
    """Su módulo incluye reglas_base.pl, así que el motor deduce sobre él sin
    que nadie le escriba una regla."""
    cliente = base_limpia
    alta = cliente.post(
        "/api/admin/casos",
        json={
            "id": "caso_de_prueba",
            "titulo": "Robo en el archivo",
            "descripcion": "Caso creado por la prueba automatizada.",
            "dificultad": "facil",
        },
    )
    assert alta.status_code == 201
    assert alta.json()["estado"] == "pendiente"

    assert "caso_de_prueba" in {c["id"] for c in cliente.get("/api/casos").json()}

    for nombre, rol in [("ana", "sospechoso"), ("beto", "victima")]:
        cliente.post(
            "/api/admin/casos/caso_de_prueba/personas",
            json={"nombre": nombre, "rol": rol},
        )
    cliente.post(
        "/api/admin/casos/caso_de_prueba/lugares",
        json={"nombre": "archivo", "descripcion": "Sala de archivo", "es_escena": True},
    )
    cliente.put(
        "/api/admin/casos/caso_de_prueba/ficha",
        json={"hora_incidente": 14, "medios_requeridos": ["llave"]},
    )
    cliente.post(
        "/api/admin/casos/caso_de_prueba/oportunidades",
        json={"tipo": "visto_en", "persona": "ana", "objeto": "archivo", "hora": 14},
    )
    cliente.post(
        "/api/admin/casos/caso_de_prueba/motivos",
        json={"persona": "ana", "tipo": "venganza"},
    )

    conclusion = cliente.get("/api/casos/caso_de_prueba/conclusion").json()
    veredicto = next(v for v in conclusion["veredictos"] if v["persona"] == "ana")
    assert veredicto["reglas_activadas"], (
        "un caso creado desde administración tiene que activar las reglas "
        "compartidas de reglas_base.pl"
    )

    assert cliente.delete("/api/admin/casos/caso_de_prueba").status_code == 200
    assert "caso_de_prueba" not in {c["id"] for c in cliente.get("/api/casos").json()}


def test_modificar_la_ficha_de_un_caso_de_fabrica(base_limpia):
    cliente = base_limpia
    cambio = cliente.put(
        "/api/admin/casos/caso1",
        json={
            "titulo": "El Collar Estelar (revisado)",
            "descripcion": "Descripción editada desde el módulo administrativo.",
            "dificultad": "dificil",
        },
    )
    assert cambio.status_code == 200
    caso = cliente.get("/api/casos/caso1").json()
    assert caso["titulo"] == "El Collar Estelar (revisado)"
    assert caso["dificultad"] == "dificil"


def test_eliminar_un_caso_de_fabrica_lo_saca_del_catalogo(base_limpia):
    cliente = base_limpia
    baja = cliente.delete("/api/admin/casos/caso3")
    assert baja.status_code == 200
    assert baja.json()["definitivo"] is False
    assert "caso3" not in {c["id"] for c in cliente.get("/api/casos").json()}
    assert cliente.get("/api/casos/caso3").status_code == 404


# --------------------------------------------------------------------------
# Persistencia y vuelta atrás
# --------------------------------------------------------------------------


def test_los_cambios_quedan_escritos_en_disco(base_limpia):
    """Es lo que hace que sobrevivan a un reinicio."""
    from app.administracion import administracion

    cliente = base_limpia
    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "testigo"},
    )
    guardado = json.loads(administracion.archivo.read_text(encoding="utf-8"))
    terminos = [operacion["termino"] for operacion in guardado["operaciones"]]
    assert "testigo(nadia_luna)" in terminos


def test_restaurar_deja_los_casos_como_estaban(cliente):
    antes = cliente.get("/api/admin/casos/caso1").json()

    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "sospechoso"},
    )
    cliente.delete("/api/admin/casos/caso1/evidencias/e1")
    cliente.put(
        "/api/admin/casos/caso1",
        json={
            "titulo": "Otro título",
            "descripcion": "Otra cosa",
            "dificultad": "facil",
        },
    )

    intervenido = cliente.get("/api/admin/casos/caso1").json()
    assert intervenido["conteos"] != antes["conteos"]

    restaurado = cliente.post("/api/admin/restaurar")
    assert restaurado.status_code == 200
    assert restaurado.json()["operaciones_deshechas"] > 0

    despues = cliente.get("/api/admin/casos/caso1").json()
    assert despues["titulo"] == antes["titulo"]
    assert despues["descripcion"] == antes["descripcion"]
    assert despues["conteos"] == antes["conteos"]
    assert despues["ficha"] == antes["ficha"]
    assert cliente.get("/api/admin/historial").json()["cambios"] == 0


def test_el_historial_registra_lo_que_se_hizo(base_limpia):
    cliente = base_limpia
    cliente.post(
        "/api/admin/casos/caso1/personas",
        json={"nombre": "nadia_luna", "rol": "testigo"},
    )
    historial = cliente.get("/api/admin/historial").json()
    assert historial["cambios"] >= 1
    ultima = historial["operaciones"][0]
    assert ultima["modulo"] == "caso1"
    assert ultima["tipo"] == "alta"
    assert ultima["termino"] == "testigo(nadia_luna)"


def test_una_baja_guarda_lo_que_se_llevo(base_limpia):
    """Sin esto una eliminación sería irreversible y restaurar no existiría."""
    cliente = base_limpia
    cliente.delete("/api/admin/casos/caso1/evidencias/e1")
    historial = cliente.get("/api/admin/historial").json()
    bajas = [op for op in historial["operaciones"] if op["tipo"] == "baja"]
    assert any(
        any(texto_hecho.startswith("evidencia(e1,") for texto_hecho in op["removidos"])
        for op in bajas
    )
