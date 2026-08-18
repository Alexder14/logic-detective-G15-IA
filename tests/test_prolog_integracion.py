"""Pruebas de integración Python <-> Prolog vía PySwip.

Estas pruebas confirman que el motor responde y que las reglas base funcionan.
Los 10 casos de prueba que exige el curso van al final del archivo, en la
sección PLANTILLA: hay uno resuelto y nueve por escribir.

Correr:
    pytest tests/ -v
"""

from __future__ import annotations

import pytest

# --------------------------------------------------------------------------
# La integración funciona
# --------------------------------------------------------------------------


def test_prolog_responde(motor):
    """Prueba de humo: PySwip ejecuta aritmética en SWI-Prolog."""
    filas = motor.filas("X is 2 + 3")
    assert filas == [{"X": 5}]


def test_la_base_de_conocimiento_esta_cargada(motor):
    """logic_detective.pl expone su versión, así que el archivo se consultó."""
    assert motor.version() == "1.0.0-esqueleto"


def test_los_cuatro_casos_estan_registrados(casos_cargados):
    """Los tres casos del entregable más el de ejemplo."""
    assert set(casos_cargados) == {"caso_demo", "caso1", "caso2", "caso3"}


def test_las_reglas_base_se_cargan_solas(motor):
    """reglas_base.pl es consultable sin ningún caso.

    Los tres casos la incluyen con `:- include`, así que un error de sintaxis
    ahí los rompe a los tres a la vez.
    """
    filas = motor.filas("caso_demo:tipo_evidencia_directa(huella)")
    assert filas, "reglas_base.pl no se cargó dentro del módulo del caso"


def test_un_caso_vacio_falla_sin_lanzar_excepcion(motor):
    """Un caso sin hechos debe fallar limpio, no explotar.

    Es lo que deja a la API en pie mientras caso1/2/3 están vacíos.
    """
    assert motor.filas("caso1:responsable(P)") == []
    assert motor.filas("caso1:sospechoso(P)") == []


def test_los_modulos_de_caso_estan_aislados(motor):
    """Los hechos de un caso no se filtran a otro.

    Así dos integrantes pueden usar los mismos nombres de sospechosos sin
    pisarse.
    """
    assert motor.filas("caso_demo:sospechoso(bruno)")
    assert motor.filas("caso2:sospechoso(bruno)") == []


# --------------------------------------------------------------------------
# Las reglas base razonan
# --------------------------------------------------------------------------


def test_detecta_contradiccion_declaracion_vs_evidencia(motor):
    """bruno niega haber estado donde su huella aparece."""
    filas = motor.filas("caso_demo:declaracion_contradice_evidencia(d1, E)")
    assert [fila["E"] for fila in filas] == ["e1"]


def test_una_coartada_sin_respaldo_es_invalida(motor):
    """La coartada de bruno no tiene quién la respalde."""
    razones = [
        fila["R"] for fila in motor.filas("caso_demo:coartada_invalida(bruno, R)")
    ]
    assert "sin_respaldo" in razones


def test_un_testigo_sospechoso_no_respalda_una_coartada(motor):
    """carla se apoya en bruno, que es sospechoso: no cuenta como respaldo."""
    assert motor.filas("caso_demo:coartada_valida(carla, _)") == []


def test_una_coartada_con_testigo_confiable_es_valida(motor):
    """La de ana sí se sostiene, y por eso no tuvo oportunidad."""
    assert motor.filas("caso_demo:coartada_valida(ana, _)")
    assert motor.filas("caso_demo:tuvo_oportunidad(ana, _)") == []


def test_nivel_sospecha_es_determinista(motor):
    """nivel_sospecha/2 da exactamente un nivel por persona.

    Comprueba que los cortes de clasificar_sospecha/2 estén bien puestos.
    """
    for persona in ("ana", "bruno", "carla"):
        filas = motor.filas(f"caso_demo:nivel_sospecha({persona}, N)")
        assert len(filas) == 1, f"{persona} obtuvo {len(filas)} niveles"


def test_la_explicacion_lista_las_reglas_activadas(motor):
    """La conclusión tiene que venir con las reglas que se usaron."""
    reglas = {
        fila["R"] for fila in motor.filas("api_explicacion(caso_demo, bruno, R, _)")
    }
    assert {"tuvo_oportunidad", "tiene_motivo", "tiene_medios"} <= reglas


def test_no_se_acusa_por_una_sola_evidencia(motor):
    """responsable/1 pide que converjan varias líneas de razonamiento.

    El enunciado lo dice: nunca acusar con una sola evidencia.
    """
    filas = motor.filas("caso_demo:evidencias_contra(bruno, E), length(E, N)")
    assert filas[0]["N"] >= 2


def test_responsable_es_una_sola_respuesta(motor):
    """El corte de responsable/1 lo vuelve semidet."""
    filas = motor.filas("caso_demo:responsable(P)")
    assert filas == [{"P": "bruno"}]


# --------------------------------------------------------------------------
# PLANTILLA — LOS 10 CASOS DE PRUEBA QUE PIDE EL CURSO
# --------------------------------------------------------------------------
#
# El enunciado exige un mínimo de 10 casos de prueba y resolver correctamente
# al menos el 80 % de las consultas evaluadas.
#
# CÓMO AGREGAR EL TUYO
#   1. Quitá el @pytest.mark.skip de la fila que te toca.
#   2. Cambiá `caso1` por tu caso y poné el resultado que TU caso debe dar.
#   3. Corré `pytest tests/ -v` y revisá que pase.
#
# Cada fila es (caso, meta_prolog, resultado_esperado).

CASOS_DE_PRUEBA = [
    # 1 — RESUELTO, sirve de ejemplo del formato.
    ("caso_demo", "responsable(P)", [{"P": "bruno"}]),
    # 2 a 10 — pendientes, uno por consulta evaluada del enunciado.
    pytest.param(
        "caso1",
        "responsable(P)",
        [{"P": "CAMBIAR"}],
        marks=pytest.mark.skip(reason="pendiente: caso1 sin hechos"),
    ),
    pytest.param(
        "caso1",
        "sospechoso_principal(P)",
        [{"P": "CAMBIAR"}],
        marks=pytest.mark.skip(reason="pendiente: caso1 sin hechos"),
    ),
    pytest.param(
        "caso1",
        "nivel_sospecha(CAMBIAR, N)",
        [{"N": "muy_alto"}],
        marks=pytest.mark.skip(reason="pendiente: caso1 sin hechos"),
    ),
    pytest.param(
        "caso2",
        "responsable(P)",
        [{"P": "CAMBIAR"}],
        marks=pytest.mark.skip(reason="pendiente: caso2 sin hechos"),
    ),
    pytest.param(
        "caso2",
        "coartada_invalida(CAMBIAR, R)",
        [{"R": "CAMBIAR"}],
        marks=pytest.mark.skip(reason="pendiente: caso2 sin hechos"),
    ),
    pytest.param(
        "caso2",
        "declaracion_contradice_evidencia(CAMBIAR, E)",
        [{"E": "CAMBIAR"}],
        marks=pytest.mark.skip(reason="pendiente: caso2 sin hechos"),
    ),
    ("caso3", "responsable(P)", [{"P": "diego_lira"}]),
    ("caso3", "tuvo_oportunidad(diego_lira, L)", [{"L": "sala_servidores"}]),
    ("caso3", "informacion_falsa(P)", [{"P": "diego_lira"}]),
]


@pytest.mark.parametrize("caso, meta, esperado", CASOS_DE_PRUEBA)
def test_caso_de_prueba(motor, caso, meta, esperado):
    """Ejecuta una consulta contra un caso y compara con el resultado esperado."""
    assert motor.filas(f"{caso}:{meta}") == esperado


def test_los_tres_casos_cumplen_los_minimos(motor):
    """Los tres casos deben alcanzar los mínimos del enunciado."""
    for caso in ("caso1", "caso2", "caso3"):
        filas = motor.filas(f"estado_caso({caso}, Estado, _)")
        assert filas[0]["Estado"] == "completo", f"{caso} no cumple los mínimos"
