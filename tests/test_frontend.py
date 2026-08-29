"""Pruebas de la interfaz web.

El backend se simula con `BackendFalso`, que imita lo que importa de la API: el
filtrado del listado, el descubrimiento progresivo (una evidencia solo se ve
después de examinarla) y la bitácora. Acá se prueba la capa de presentación
—rutas, plantillas y qué información llega al HTML—; la inferencia se prueba en
test_prolog_integracion.py y la API en test_api.py.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs

import pytest


def caso(id_, dificultad, estado):
    return {
        "id": id_,
        "titulo": f"Caso {id_}",
        "descripcion": "Descripción de prueba.",
        "dificultad": dificultad,
        "estado": estado,
        "es_ejemplo": id_ == "caso_demo",
        "conteos": {
            "sospechosos": 4,
            "evidencias": 10,
            "lugares": 5,
            "declaraciones": 5,
            "reglas_de_inferencia": 12,
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

# --------------------------------------------------------------------------
# Datos del módulo administrativo
# --------------------------------------------------------------------------

#: Copia de lo que publica /api/admin/esquema, con la misma forma.
ESQUEMA = {
    "dificultades": ["facil", "media", "dificil"],
    "roles": ["sospechoso", "testigo", "victima"],
    "tipos_relacion": ["socio", "rival", "empleado", "heredero"],
    "tipos_motivo": ["deuda", "herencia", "venganza"],
    "medios": ["llave", "codigo_alarma", "fuerza"],
    "tipos_evidencia": ["huella", "video", "documento"],
    "tipos_declaracion": {
        "estuvo_en": ["persona", "lugar", "hora"],
        "no_estuvo_en": ["persona", "lugar", "hora"],
        "posee": ["persona", "medio"],
    },
    "tipos_respaldo": {
        "testigo": "persona",
        "camara": "lugar",
        "documento": "evidencia",
        "ninguno": None,
    },
    "tipos_oportunidad": {
        "visto_en": {"objeto": "lugar", "hora": True},
        "posee_medio": {"objeto": "medio", "hora": False},
    },
}

#: Qué campos identifican a cada entidad, igual que en la API real.
CLAVES_ADMIN = {
    "personas": ("nombre",),
    "lugares": ("nombre",),
    "evidencias": ("id",),
    "declaraciones": ("id",),
    "relaciones": ("persona", "con_quien"),
    "coartadas": ("persona",),
    "motivos": ("persona", "tipo"),
    "oportunidades": ("tipo", "persona", "objeto", "hora"),
}

ADMIN_INICIAL = {
    "personas": [
        {"nombre": "victor_cordero", "rol": "sospechoso"},
        {"nombre": "bruno_salcedo", "rol": "testigo"},
        {"nombre": "adriana_belmonte", "rol": "victima"},
    ],
    "lugares": [
        {
            "nombre": "salon_principal",
            "descripcion": "Salón principal de la gala",
            "es_escena": True,
            "conectado_con": ["guardarropa"],
        },
        {
            "nombre": "guardarropa",
            "descripcion": "Guardarropa junto al salón",
            "es_escena": False,
            "conectado_con": [],
        },
    ],
    "evidencias": [
        {
            "id": "e1",
            "tipo": "huella",
            "lugar": "salon_principal",
            "hora": 22,
            "descripcion": "Huella parcial en la vitrina",
            "incrimina": ["victor_cordero"],
        }
    ],
    "declaraciones": [
        {
            "id": "d1",
            "autor": "bruno_salcedo",
            "tipo": "estuvo_en",
            "contenido": "estuvo_en(victor_cordero,salon_principal,22)",
        }
    ],
    "relaciones": [
        {
            "persona": "victor_cordero",
            "con_quien": "adriana_belmonte",
            "tipo": "empleado",
        }
    ],
    "coartadas": [
        {
            "persona": "victor_cordero",
            "lugar": "guardarropa",
            "hora": 22,
            "respaldo": "ninguno",
            "veredicto": {"estado": "invalida", "detalle": "sin_respaldo"},
        }
    ],
    "motivos": [{"persona": "victor_cordero", "tipo": "deuda"}],
    "oportunidades": [
        {
            "tipo": "visto_en",
            "persona": "victor_cordero",
            "objeto": "salon_principal",
            "hora": 22,
        }
    ],
}

EVIDENCIAS = [
    {
        "id": "e1",
        "tipo": "huella",
        "lugar": "salon_principal",
        "hora": 22,
        "descripcion": "Huella parcial en la vitrina forzada.",
        "es_directa": True,
        "incrimina": ["victor_cordero"],
    },
    {
        "id": "e2",
        "tipo": "video",
        "lugar": "guardarropa",
        "hora": 22,
        "descripcion": "Grabación del pasillo del guardarropa.",
        "es_directa": False,
        "incrimina": [],
    },
]

DECLARACIONES = [
    {
        "id": "d1",
        "autor": "victor_cordero",
        "contenido": "no_estuvo_en(victor_cordero,salon_principal,22)",
    },
    {
        "id": "d2",
        "autor": "bruno_salcedo",
        "contenido": "vio_a(victor_cordero,salon_principal,22)",
    },
]

SOSPECHOSOS = [
    {
        "persona": "victor_cordero",
        "nivel_sospecha": "muy_alto",
        "puntaje": 18,
        "indicios": ["coartada_invalida", "oportunidad"],
    },
    {"persona": "hugo_paredes", "nivel_sospecha": "bajo", "puntaje": 3, "indicios": []},
]

COARTADAS = [
    {
        "persona": "victor_cordero",
        "estado": "invalida",
        "detalle": "contradice_evidencia(e1)",
    }
]

PISTAS = ["revisar_coartada_de(victor_cordero)", "revisar_evidencia(e1)"]

CONCLUSION = {
    "caso": "caso1",
    "concluye": True,
    "responsable": "victor_cordero",
    "sospechosos_principales": ["victor_cordero"],
    "posibles_complices": [],
    "veredictos": [
        {
            "persona": "victor_cordero",
            "veredicto": "responsable",
            "nivel_sospecha": "muy_alto",
            "puntaje": 18,
            "reglas_activadas": [
                {"regla": "coartada_invalida", "detalle": "su coartada choca con e1"}
            ],
        }
    ],
}

#: Lo que devuelve cada análisis del panel.
ANALISIS = {
    "sospechosos": SOSPECHOSOS,
    "lugares": [
        {
            "nombre": "salon_principal",
            "descripcion": "Salón del evento.",
            "es_escena": True,
        }
    ],
    "coartadas": COARTADAS,
    "relaciones": [
        {
            "persona": "isabela_duarte",
            "con_quien": "adriana_belmonte",
            "tipo": "heredero",
            "es_conflictiva": True,
            "es_con_la_victima": True,
        }
    ],
    "motivos": [{"persona": "victor_cordero", "motivo": "deuda_con_la_victima"}],
    "oportunidades": [{"persona": "victor_cordero", "lugar": "salon_principal"}],
    "contradicciones": [{"tipo": "declaracion_vs_evidencia", "a": "d1", "b": "e1"}],
    "linea-temporal": [
        {"hora": 22, "tipo": "evidencia", "detalle": "huella en la vitrina"}
    ],
}


class BackendFalso:
    """Imitación de la API, con el estado de las investigaciones en memoria."""

    def __init__(self, error_backend):
        self.ErrorBackend = error_backend
        self.investigaciones: dict[str, dict] = {}
        self.creadas = 0
        self.admin = {k: [dict(f) for f in v] for k, v in ADMIN_INICIAL.items()}
        self.operaciones = []
        self.casos_creados = set()
        self.casos_eliminados = set()

    # -- estado de una investigación ----------------------------------------

    def _crear(self, caso_id: str) -> dict:
        self.creadas += 1
        investigacion = {
            "id": f"inv{self.creadas}",
            "caso_id": caso_id,
            "puntaje": 100,
            "examinadas": [],
            "interrogadas": [],
            "pistas": [],
            "bitacora": [],
        }
        self.investigaciones[investigacion["id"]] = investigacion
        return investigacion

    def _exigir(self, investigacion_id: str) -> dict:
        investigacion = self.investigaciones.get(investigacion_id)
        if investigacion is None:
            raise self.ErrorBackend(
                f"404: La investigación '{investigacion_id}' no existe", 404
            )
        return investigacion

    def _registrar(self, investigacion: dict, tipo: str, detalle: str) -> None:
        investigacion["bitacora"].append(
            {"tipo": tipo, "detalle": detalle, "momento": "2026-08-18T21:15:37+00:00"}
        )

    # -- enrutado ------------------------------------------------------------

    # -- módulo administrativo ---------------------------------------------
    #
    # En memoria y con la forma que devuelve la API real. Acá se prueba la capa
    # de presentación; que el `assertz` llegue a Prolog se prueba en
    # test_admin.py, contra el motor de verdad.

    def _admin_ficha(self, caso_id):
        for c in CASOS:
            if c["id"] == caso_id:
                ficha = dict(c)
                ficha["creado_en_administracion"] = caso_id in self.casos_creados
                ficha["ficha"] = {
                    "escena_del_incidente": ["salon_principal"],
                    "hora_del_incidente": [22],
                    "medio_requerido": ["llave"],
                }
                return ficha
        raise self.ErrorBackend("404: El caso no existe", 404)

    def _admin_clave(self, entidad, fila):
        return tuple(str(fila.get(nombre, "")) for nombre in CLAVES_ADMIN[entidad])

    def _admin_registrar(self, tipo, termino):
        self.operaciones.insert(
            0, {"modulo": "caso1", "tipo": tipo, "termino": termino, "removidos": []}
        )

    def _admin(self, ruta, metodo, json, parametros):
        """Atiende /api/admin/*. Devuelve None si la ruta no es suya.

        La clave de una oportunidad viaja en la query string; `requests` la
        separaría solo, acá hay que hacerlo a mano.
        """
        ruta, _, consulta = ruta.partition("?")
        if consulta:
            parametros = {
                **parametros,
                **{clave: valores[0] for clave, valores in parse_qs(consulta).items()},
            }
        if ruta == "/api/admin/esquema":
            return ESQUEMA
        if ruta == "/api/admin/historial":
            return {
                "cambios": len(self.operaciones),
                "casos_creados": sorted(self.casos_creados),
                "casos_eliminados": sorted(self.casos_eliminados),
                "operaciones": list(self.operaciones),
            }
        if ruta == "/api/admin/restaurar" and metodo == "POST":
            deshechas = len(self.operaciones)
            self.operaciones.clear()
            self.casos_creados.clear()
            self.casos_eliminados.clear()
            self.admin = {k: [dict(f) for f in v] for k, v in ADMIN_INICIAL.items()}
            return {"estado": "restaurado", "operaciones_deshechas": deshechas}

        if ruta == "/api/admin/casos" and metodo == "POST":
            self.casos_creados.add(json["id"])
            self._admin_registrar("alta", f"caso({json['id']},...)")
            return {"id": json["id"], "titulo": json["titulo"], "estado": "pendiente"}

        coincide = re.fullmatch(r"/api/admin/casos/([^/]+)", ruta)
        if coincide:
            caso_id = coincide.group(1)
            if metodo == "DELETE":
                definitivo = caso_id in self.casos_creados
                self.casos_creados.discard(caso_id)
                if not definitivo:
                    self.casos_eliminados.add(caso_id)
                return {"eliminado": caso_id, "definitivo": definitivo}
            if metodo == "PUT":
                self._admin_registrar("alta", f"caso({caso_id},...)")
                return self._admin_ficha(caso_id)
            return self._admin_ficha(caso_id)

        coincide = re.fullmatch(r"/api/admin/casos/([^/]+)/ficha", ruta)
        if coincide and metodo == "PUT":
            self._admin_registrar("alta", "escena_del_incidente(salon_principal)")
            return self._admin_ficha(coincide.group(1))

        coincide = re.fullmatch(
            rf"/api/admin/casos/([^/]+)/({'|'.join(CLAVES_ADMIN)})(?:/(.+))?", ruta
        )
        if coincide is None:
            return None
        caso_id, entidad, resto = coincide.groups()
        self._admin_ficha(caso_id)  # 404 si el caso no existe
        filas = self.admin[entidad]

        if metodo == "GET":
            return [dict(fila) for fila in filas]

        if metodo == "POST":
            nueva = dict(json)
            if any(
                self._admin_clave(entidad, f) == self._admin_clave(entidad, nueva)
                for f in filas
            ):
                raise self.ErrorBackend("400: ya existe ese registro", 400)
            filas.append(nueva)
            self._admin_registrar("alta", f"{entidad}: {nueva}")
            return nueva

        if entidad == "oportunidades":
            clave = tuple(
                str(parametros.get(nombre, "")) for nombre in CLAVES_ADMIN[entidad]
            )
        else:
            clave = tuple(resto.split("/")) if resto else ()

        for indice, fila in enumerate(filas):
            if self._admin_clave(entidad, fila) == clave:
                if metodo == "DELETE":
                    filas.pop(indice)
                    self._admin_registrar("baja", f"{entidad}: {clave}")
                    return {"eliminada": clave[0], "en_cascada": {}}
                fila.update(json)
                self._admin_registrar("alta", f"{entidad}: {fila}")
                return dict(fila)
        raise self.ErrorBackend("404: no existe ese registro", 404)

    def __call__(self, ruta, metodo="GET", json=None, **parametros):
        investigacion_id = parametros.get("investigacion_id")

        if ruta.startswith("/api/admin/") and ruta != "/api/admin/estado":
            respuesta = self._admin(ruta, metodo, json, parametros)
            if respuesta is not None:
                return respuesta

        if ruta == "/api/casos":
            casos = list(CASOS)
            for campo in ("dificultad", "estado"):
                if parametros.get(campo):
                    casos = [c for c in casos if c[campo] == parametros[campo]]
            return casos

        if ruta == "/api/admin/estado":
            return {
                "minimos_por_caso": {
                    "sospechosos": 4,
                    "evidencias": 10,
                    "lugares": 5,
                    "declaraciones": 5,
                    "reglas_de_inferencia": 10,
                },
                "casos": list(CASOS),
                "prolog": {"disponible": True, "error": None},
            }

        coincide = re.fullmatch(r"/api/casos/([^/]+)", ruta)
        if coincide:
            for c in CASOS:
                if c["id"] == coincide.group(1):
                    return c
            raise self.ErrorBackend("404: El caso no existe", 404)

        coincide = re.fullmatch(r"/api/casos/([^/]+)/investigaciones", ruta)
        if coincide and metodo == "POST":
            nueva = self._crear(coincide.group(1))
            return {
                "investigacion_id": nueva["id"],
                "caso_id": nueva["caso_id"],
                "puntaje": nueva["puntaje"],
            }

        coincide = re.fullmatch(
            r"/api/casos/([^/]+)/investigaciones/([^/]+)/bitacora", ruta
        )
        if coincide:
            investigacion = self._exigir(coincide.group(2))
            return {
                "investigacion_id": investigacion["id"],
                "caso_id": coincide.group(1),
                "puntaje": investigacion["puntaje"],
                "acciones": list(investigacion["bitacora"]),
            }

        coincide = re.fullmatch(
            r"/api/casos/([^/]+)/investigaciones/([^/]+)/informe", ruta
        )
        if coincide:
            investigacion = self._exigir(coincide.group(2))
            return {
                "caso": coincide.group(1),
                "investigacion_id": investigacion["id"],
                "puntaje_final": investigacion["puntaje"],
                "avance": {
                    "evidencias_examinadas": len(investigacion["examinadas"]),
                    "evidencias_totales": len(EVIDENCIAS),
                    "declaraciones_interrogadas": len(investigacion["interrogadas"]),
                    "declaraciones_totales": len(DECLARACIONES),
                    "pistas_usadas": len(investigacion["pistas"]),
                    "pistas_totales": len(PISTAS),
                },
                "bitacora": list(investigacion["bitacora"]),
                "conclusion": CONCLUSION,
            }

        coincide = re.fullmatch(
            r"/api/casos/([^/]+)/investigaciones/([^/]+)/evidencias/([^/]+)/examinar",
            ruta,
        )
        if coincide:
            investigacion = self._exigir(coincide.group(2))
            evidencia = next(e for e in EVIDENCIAS if e["id"] == coincide.group(3))
            if evidencia["id"] not in investigacion["examinadas"]:
                investigacion["examinadas"].append(evidencia["id"])
            self._registrar(
                investigacion, "consultar", f"examinó la evidencia {evidencia['id']}"
            )
            return dict(evidencia)

        coincide = re.fullmatch(
            r"/api/casos/([^/]+)/investigaciones/([^/]+)/declaraciones/([^/]+)/interrogar",
            ruta,
        )
        if coincide:
            investigacion = self._exigir(coincide.group(2))
            declaracion = next(d for d in DECLARACIONES if d["id"] == coincide.group(3))
            if declaracion["id"] not in investigacion["interrogadas"]:
                investigacion["interrogadas"].append(declaracion["id"])
            self._registrar(
                investigacion,
                "interrogar",
                f"interrogó la declaración {declaracion['id']} de {declaracion['autor']}",
            )
            return dict(declaracion)

        coincide = re.fullmatch(
            r"/api/casos/([^/]+)/investigaciones/([^/]+)/pistas/siguiente", ruta
        )
        if coincide:
            investigacion = self._exigir(coincide.group(2))
            disponibles = [p for p in PISTAS if p not in investigacion["pistas"]]
            if not disponibles:
                raise self.ErrorBackend("404: No quedan más pistas", 404)
            pista = disponibles[0]
            investigacion["pistas"].append(pista)
            investigacion["puntaje"] -= 5
            self._registrar(investigacion, "pedir_ayuda", f"pidió la pista: {pista}")
            return {
                "pista": pista,
                "puntaje": investigacion["puntaje"],
                "pistas_restantes": len(disponibles) - 1,
            }

        # Todas las pistas del caso, sin costo. La interfaz solo usa el total.
        coincide = re.fullmatch(r"/api/casos/([^/]+)/pistas", ruta)
        if coincide:
            return list(PISTAS)

        coincide = re.fullmatch(r"/api/casos/([^/]+)/(evidencias|declaraciones)", ruta)
        if coincide:
            es_evidencia = coincide.group(2) == "evidencias"
            todos = EVIDENCIAS if es_evidencia else DECLARACIONES
            if investigacion_id is None:
                return [dict(x) for x in todos]
            investigacion = self._exigir(investigacion_id)
            clave = "examinadas" if es_evidencia else "interrogadas"
            return [dict(x) for x in todos if x["id"] in investigacion[clave]]

        coincide = re.fullmatch(rf"/api/casos/([^/]+)/({'|'.join(ANALISIS)})", ruta)
        if coincide:
            if investigacion_id is not None:
                self._registrar(
                    self._exigir(investigacion_id),
                    "analizar",
                    f"analizó {coincide.group(2)}",
                )
            return [dict(x) for x in ANALISIS[coincide.group(2)]]

        coincide = re.fullmatch(r"/api/casos/([^/]+)/acusacion", ruta)
        if coincide and metodo == "POST":
            acusado = json["sospechoso"]
            veredicto = (
                "correcta" if acusado == CONCLUSION["responsable"] else "incorrecta"
            )
            if json.get("investigacion_id"):
                self._registrar(
                    self._exigir(json["investigacion_id"]),
                    "acusar",
                    f"acusó a {acusado}: veredicto {veredicto}",
                )
            return {
                "caso": coincide.group(1),
                "acusado": acusado,
                "veredicto": veredicto,
                "responsable_segun_el_motor": CONCLUSION["responsable"],
                "reglas_activadas": [],
            }

        raise AssertionError(f"ruta no simulada: {metodo} {ruta} {parametros}")


@pytest.fixture(autouse=True)
def backend(interfaz, monkeypatch):
    """Reemplaza las llamadas HTTP al backend por el backend falso."""
    falso = BackendFalso(interfaz.ErrorBackend)
    monkeypatch.setattr(interfaz, "api", falso)
    return falso


@pytest.fixture
def investigacion(navegador, backend):
    """Abre una investigación sobre caso1 y devuelve su estado en el backend."""
    navegador.post("/investigacion/caso1/abrir")
    return next(iter(backend.investigaciones.values()))


def texto(respuesta) -> str:
    return respuesta.get_data(as_text=True)


# --------------------------------------------------------------------------
# Parámetros de la URL (lógica pura)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("basura", ["", None, "MEDIANA", "'; drop", "facil2"])
def test_una_dificultad_invalida_se_ignora(interfaz, basura):
    """La URL la puede escribir el usuario: un valor raro no se le reenvía al
    backend, que responde 400 a lo que no sea un átomo de Prolog."""
    assert interfaz.opcion(basura, interfaz.DIFICULTADES) == ""


def test_una_dificultad_valida_se_normaliza(interfaz):
    assert interfaz.opcion("  FACIL ", interfaz.DIFICULTADES) == "facil"


def test_los_conteos_cubren_todos_los_valores(interfaz):
    conteos = interfaz.contar_por(CASOS, "dificultad", interfaz.DIFICULTADES)
    assert conteos == {"facil": 1, "media": 2, "dificil": 1}


@pytest.mark.parametrize(
    "termino, esperado",
    [
        ("revisar_evidencia(e3)", "Revisá la evidencia e3."),
        (
            "revisar_coartada_de(victor_cordero)",
            "Revisá la coartada de Victor Cordero.",
        ),
        # Una forma que la interfaz no conoce se muestra cruda antes que perderla.
        ("inventada(x)", "inventada(x)"),
        ("texto suelto", "texto suelto"),
    ],
)
def test_las_pistas_se_leen_en_castellano(interfaz, termino, esperado):
    assert interfaz.pista_legible(termino) == esperado


def test_un_indicio_nuevo_del_motor_no_se_pierde(interfaz):
    """Si Prolog agrega un indicio, se ve legible sin tocar la interfaz."""
    assert interfaz.indicio_legible("coartada_invalida") == "coartada inválida"
    assert interfaz.indicio_legible("indicio_nuevo") == "Indicio Nuevo"


def test_el_descubrimiento_oculta_lo_no_hallado(interfaz):
    """De lo que no se descubrió solo puede sobrevivir el id."""
    fusion = interfaz.descubrimiento(EVIDENCIAS, [EVIDENCIAS[0]], ("id",))
    hallado, por_hallar = fusion
    assert hallado["descubierto"] and hallado["descripcion"]
    assert por_hallar == {"id": "e2", "descubierto": False}


def test_las_pistas_salen_de_la_bitacora(interfaz):
    acciones = [
        {"tipo": "consultar", "detalle": "examinó la evidencia e1", "momento": ""},
        {
            "tipo": "pedir_ayuda",
            "detalle": "pidió la pista: revisar(e1)",
            "momento": "",
        },
    ]
    assert interfaz.pistas_pedidas(acciones) == ["revisar(e1)"]


# --------------------------------------------------------------------------
# Listado de casos
# --------------------------------------------------------------------------


def test_el_listado_muestra_todos_los_casos(navegador):
    html = texto(navegador.get("/investigacion"))
    for c in CASOS:
        assert c["titulo"] in html


def test_el_listado_le_pasa_el_filtro_al_backend(navegador):
    """El filtrado lo hace el backend; la interfaz solo reenvía el parámetro."""
    html = texto(navegador.get("/investigacion?dificultad=dificil"))
    assert "Caso caso3" in html
    assert "Caso caso1" not in html


def test_los_contadores_cuentan_sobre_todos_los_casos(navegador):
    """Filtrar no debe cambiar los contadores de los chips."""
    html = texto(navegador.get("/investigacion?dificultad=dificil"))
    assert 'Todas <span class="chip-n">4</span>' in re.sub(r"\s+", " ", html)


def test_un_filtro_invalido_no_rompe_el_listado(navegador):
    respuesta = navegador.get("/investigacion?dificultad=inventada")
    assert respuesta.status_code == 200
    assert "Caso caso1" in texto(respuesta)


def test_un_filtro_sin_resultados_avisa(navegador):
    html = texto(navegador.get("/investigacion?dificultad=dificil&estado=completo"))
    assert "Ningún caso coincide" in html


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
    assert "No hay casos con datos cargados" in texto(
        navegador.get(respuesta.headers["Location"])
    )


# --------------------------------------------------------------------------
# Expediente y descubrimiento progresivo
# --------------------------------------------------------------------------


def test_el_expediente_cerrado_no_revela_nada(navegador):
    """Sin investigación abierta no puede llegar al HTML nada por descubrir."""
    html = texto(navegador.get("/investigacion/caso1"))
    assert "Abrir la investigación" in html
    for evidencia in EVIDENCIAS:
        assert evidencia["descripcion"] not in html
    for declaracion in DECLARACIONES:
        assert declaracion["contenido"] not in html


def test_un_caso_que_no_existe_da_404(navegador):
    assert navegador.get("/investigacion/inventado").status_code == 404


def test_abrir_la_investigacion_muestra_el_panel(navegador, backend):
    navegador.post("/investigacion/caso1/abrir")
    assert len(backend.investigaciones) == 1

    html = texto(navegador.get("/investigacion/caso1"))
    assert "Bitácora de investigación" in html
    assert "sin examinar" in html
    # El puntaje inicial, en el marcador.
    assert "100" in html


def test_una_evidencia_sin_examinar_solo_muestra_su_id(navegador, investigacion):
    html = texto(navegador.get("/investigacion/caso1"))
    assert "e1" in html
    assert EVIDENCIAS[0]["descripcion"] not in html


def test_examinar_revela_la_evidencia_y_la_anota(navegador, investigacion):
    navegador.post("/investigacion/caso1/evidencias/e1/examinar")
    assert investigacion["examinadas"] == ["e1"]

    html = texto(navegador.get("/investigacion/caso1"))
    assert EVIDENCIAS[0]["descripcion"] in html
    assert "examinó la evidencia e1" in html
    # La otra evidencia sigue sin descubrirse.
    assert EVIDENCIAS[1]["descripcion"] not in html


def test_interrogar_revela_la_declaracion(navegador, investigacion):
    html = texto(navegador.get("/investigacion/caso1"))
    assert DECLARACIONES[0]["contenido"] not in html
    # El autor sí se conoce de antemano: a quién interrogar no es un secreto.
    assert "Victor Cordero" in html

    navegador.post("/investigacion/caso1/declaraciones/d1/interrogar")
    html = texto(navegador.get("/investigacion/caso1"))
    assert DECLARACIONES[0]["contenido"] in html
    assert "interrogó la declaración d1" in html


def test_el_panel_no_revela_las_pistas_no_pedidas(navegador, investigacion):
    """La interfaz pide todas las pistas para saber cuántas hay, pero el texto
    de una pista solo aparece cuando el detective la pagó."""
    html = texto(navegador.get("/investigacion/caso1"))
    assert f"0 de {len(PISTAS)}" in html
    for pista in PISTAS:
        assert pista not in html


def test_pedir_una_pista_descuenta_puntaje(navegador, investigacion):
    navegador.post("/investigacion/caso1/pista")
    assert investigacion["puntaje"] == 95

    html = texto(navegador.get("/investigacion/caso1"))
    assert PISTAS[0] in html
    assert "95" in html


def test_la_pista_se_muestra_leida_y_con_el_termino_del_motor(navegador, investigacion):
    """El término es lo que prueba que la pista la eligió Prolog."""
    navegador.post("/investigacion/caso1/pista")
    html = texto(navegador.get("/investigacion/caso1"))
    assert "Revisá la coartada de Victor Cordero." in html
    assert PISTAS[0] in html


def test_los_indicios_se_muestran_legibles(navegador, investigacion):
    html = texto(navegador.get("/investigacion/caso1?analisis=sospechosos"))
    assert "coartada inválida" in html
    assert "tuvo oportunidad" in html


def test_las_pistas_agotadas_avisan_sin_romper(navegador, investigacion):
    for _ in range(len(PISTAS)):
        navegador.post("/investigacion/caso1/pista")
    respuesta = navegador.post("/investigacion/caso1/pista", follow_redirects=True)
    assert respuesta.status_code == 200
    assert "No quedan más pistas" in texto(respuesta)


def test_un_analisis_queda_registrado_en_la_bitacora(navegador, investigacion):
    html = texto(navegador.get("/investigacion/caso1?analisis=coartadas"))
    assert COARTADAS[0]["detalle"] in html
    assert [a["tipo"] for a in investigacion["bitacora"]] == ["analizar"]


def test_todos_los_analisis_de_la_interfaz_estan_simulados(interfaz):
    """Si se agrega un análisis, esta prueba obliga a cubrirlo también acá."""
    assert set(interfaz.ANALISIS) == set(ANALISIS)


def test_el_analisis_de_relaciones_marca_las_conflictivas(navegador, investigacion):
    html = texto(navegador.get("/investigacion/caso1?analisis=relaciones"))
    assert "Adriana Belmonte" in html
    assert "conflictiva" in html


def test_un_analisis_inventado_se_ignora(navegador, investigacion):
    respuesta = navegador.get("/investigacion/caso1?analisis=todo")
    assert respuesta.status_code == 200
    assert investigacion["bitacora"] == []


def test_abrir_el_panel_no_ensucia_la_bitacora(navegador, investigacion):
    """Solo las acciones del detective se registran, no cada render de la página.

    Es la razón por la que los análisis son enlaces aparte y no se cargan todos
    al entrar al caso.
    """
    for _ in range(3):
        navegador.get("/investigacion/caso1")
    assert investigacion["bitacora"] == []


def test_las_acciones_conservan_el_analisis_abierto(navegador, investigacion):
    respuesta = navegador.post(
        "/investigacion/caso1/evidencias/e1/examinar", data={"analisis": "coartadas"}
    )
    assert "analisis=coartadas" in respuesta.headers["Location"]


def test_sin_investigacion_no_se_puede_examinar(navegador, backend):
    respuesta = navegador.post(
        "/investigacion/caso1/evidencias/e1/examinar", follow_redirects=True
    )
    assert "Primero hay que abrir la investigación" in texto(respuesta)
    assert backend.investigaciones == {}


def test_reiniciar_abre_una_investigacion_nueva(navegador, investigacion):
    navegador.post("/investigacion/caso1/evidencias/e1/examinar")
    navegador.post("/investigacion/caso1/abrir")

    html = texto(navegador.get("/investigacion/caso1"))
    assert "Sin acciones todavía" in html
    assert EVIDENCIAS[0]["descripcion"] not in html


def test_una_investigacion_perdida_se_olvida(navegador):
    """El backend guarda las investigaciones en memoria: si se reinicia, la
    cookie apunta a una que ya no existe."""
    with navegador.session_transaction() as sesion:
        sesion["investigaciones"] = {"caso1": "inv-fantasma"}

    respuesta = navegador.get("/investigacion/caso1")
    assert "ya no está en el servidor" in texto(respuesta)

    # Y no vuelve a avisar: la cookie quedó limpia.
    assert "ya no está en el servidor" not in texto(
        navegador.get("/investigacion/caso1")
    )


# --------------------------------------------------------------------------
# Acusación e informe final
# --------------------------------------------------------------------------


def test_una_acusacion_correcta_queda_en_la_bitacora(navegador, investigacion):
    respuesta = navegador.post(
        "/investigacion/caso1/acusacion",
        data={"sospechoso": "victor_cordero"},
        follow_redirects=True,
    )
    assert "Acusación correcta" in texto(respuesta)
    assert investigacion["bitacora"][-1]["tipo"] == "acusar"


def test_una_acusacion_incorrecta_dice_a_quien_senala_el_motor(
    navegador, investigacion
):
    respuesta = navegador.post(
        "/investigacion/caso1/acusacion",
        data={"sospechoso": "hugo_paredes"},
        follow_redirects=True,
    )
    assert "Acusación incorrecta" in texto(respuesta)
    assert "Victor Cordero" in texto(respuesta)


def test_acusar_sin_elegir_a_nadie_avisa(navegador, investigacion):
    respuesta = navegador.post(
        "/investigacion/caso1/acusacion", data={}, follow_redirects=True
    )
    assert "Elegí a un sospechoso" in texto(respuesta)


def test_el_informe_final_muestra_la_conclusion_y_la_bitacora(navegador, investigacion):
    navegador.post("/investigacion/caso1/evidencias/e1/examinar")
    html = texto(navegador.get("/investigacion/caso1/informe"))

    assert "Informe final" in html
    assert "Victor Cordero" in html
    # La justificación que pide la rúbrica: la regla que se activó.
    assert "coartada_invalida" in html
    assert "examinó la evidencia e1" in html


def test_el_informe_sin_investigacion_vuelve_al_caso(navegador):
    respuesta = navegador.get("/investigacion/caso1/informe", follow_redirects=True)
    assert "Primero hay que abrir la investigación" in texto(respuesta)


# --------------------------------------------------------------------------
# Módulo administrativo
# --------------------------------------------------------------------------


def test_admin_muestra_el_avance_de_los_casos(navegador):
    html = texto(navegador.get("/admin"))
    assert "Caso caso1" in html
    assert "/admin/casos/caso1" in html
    assert "Administrar" in html


def test_admin_muestra_las_reglas_de_inferencia_por_caso(navegador):
    html = texto(navegador.get("/admin"))
    assert "Reglas" in html
    assert "12/10" in html


def test_admin_lista_las_investigaciones_de_la_sesion(navegador, investigacion):
    navegador.post("/investigacion/caso1/pista")
    html = texto(navegador.get("/admin"))
    assert "Investigaciones de esta sesión" in html
    assert "95" in html
    assert "Ver informe" in html


def test_admin_marca_como_expirada_una_investigacion_perdida(navegador):
    with navegador.session_transaction() as sesion:
        sesion["investigaciones"] = {"caso1": "inv-fantasma"}
    assert "expirada" in texto(navegador.get("/admin"))


def test_admin_explica_por_que_el_caso_de_ejemplo_esta_incompleto(navegador):
    """En el módulo administrativo "incompleto" se lee como trabajo a medias."""
    html = texto(navegador.get("/admin"))
    assert "ejemplo" in html
    assert "no es uno de los tres casos entregables" in html


def test_el_expediente_del_caso_de_ejemplo_lo_aclara(navegador):
    html = texto(navegador.get("/investigacion/caso_demo"))
    assert "Caso de referencia" in html


def test_admin_sin_investigaciones_lo_dice(navegador):
    assert "No hay investigaciones abiertas" in texto(navegador.get("/admin"))


# --------------------------------------------------------------------------
# Varios
# --------------------------------------------------------------------------


def test_el_menu_marca_el_modulo_activo(navegador):
    assert 'aria-current="page"' in texto(navegador.get("/investigacion"))


def test_el_menu_marca_investigacion_dentro_de_un_caso(navegador):
    html = texto(navegador.get("/investigacion/caso1"))
    assert 'aria-current="page"' in html


def test_la_pagina_de_inicio_responde(navegador):
    assert navegador.get("/").status_code == 200


def test_el_healthcheck_de_la_interfaz_responde(navegador):
    assert navegador.get("/salud").get_json()["estado"] == "ok"


# --------------------------------------------------------------------------
# Interfaz del módulo administrativo
# --------------------------------------------------------------------------


def test_el_editor_de_un_caso_muestra_las_ocho_entidades(navegador):
    """Una sola pantalla con todo lo editable del caso."""
    html = texto(navegador.get("/admin/casos/caso1"))
    for entidad in (
        "personas",
        "lugares",
        "evidencias",
        "declaraciones",
        "relaciones",
        "coartadas",
        "motivos",
        "oportunidades",
    ):
        assert f'id="{entidad}"' in html, f"falta la sección de {entidad}"


def test_el_editor_ofrece_solo_valores_del_esquema(navegador):
    """Los desplegables salen del esquema, así que no proponen tipos que
    reglas_base.pl no sepa interpretar."""
    html = texto(navegador.get("/admin/casos/caso1"))
    for tipo in ESQUEMA["tipos_motivo"]:
        assert f'value="{tipo}"' in html


def test_el_editor_solo_ofrece_personas_y_lugares_del_caso(navegador):
    """Las opciones que dependen del caso las arma la vista con lo que existe."""
    html = texto(navegador.get("/admin/casos/caso1"))
    assert 'value="victor_cordero"' in html
    assert 'value="salon_principal"' in html
    assert 'value="persona_de_otro_caso"' not in html


def test_editar_una_fila_la_abre_como_formulario(navegador):
    html = texto(navegador.get("/admin/casos/caso1?editar=personas:victor_cordero"))
    assert "fila-en-edicion" in html
    assert "no se pueden cambiar" in html


def test_un_caso_inexistente_da_404(navegador):
    assert navegador.get("/admin/casos/inventado").status_code == 404


def test_una_entidad_inexistente_da_404(navegador):
    assert (
        navegador.post(
            "/admin/casos/caso1/inventadas/crear", data={"x": "1"}
        ).status_code
        == 404
    )


def test_alta_de_una_persona_desde_el_formulario(navegador, backend):
    respuesta = navegador.post(
        "/admin/casos/caso1/personas/crear",
        data={"nombre": "nadia_luna", "rol": "testigo"},
    )
    assert respuesta.status_code == 302
    assert {"nombre": "nadia_luna", "rol": "testigo"} in backend.admin["personas"]


def test_el_alta_manda_las_listas_como_listas(navegador, backend):
    """Las casillas múltiples llegan repetidas: tienen que viajar como lista."""
    navegador.post(
        "/admin/casos/caso1/evidencias/crear",
        data={
            "id": "e9",
            "tipo": "video",
            "lugar": "salon_principal",
            "hora": "22",
            "descripcion": "Cámara lateral",
            "incrimina": ["victor_cordero", "bruno_salcedo"],
        },
    )
    nueva = next(e for e in backend.admin["evidencias"] if e["id"] == "e9")
    assert nueva["incrimina"] == ["victor_cordero", "bruno_salcedo"]


def test_una_evidencia_sin_hora_se_manda_como_desconocida(navegador, backend):
    navegador.post(
        "/admin/casos/caso1/evidencias/crear",
        data={
            "id": "e10",
            "tipo": "documento",
            "lugar": "guardarropa",
            "hora": "",
            "descripcion": "Registro sin hora",
        },
    )
    nueva = next(e for e in backend.admin["evidencias"] if e["id"] == "e10")
    assert nueva["hora"] == "desconocida"


def test_la_casilla_de_escena_viaja_como_booleano(navegador, backend):
    navegador.post(
        "/admin/casos/caso1/lugares/crear",
        data={
            "nombre": "terraza",
            "descripcion": "Terraza exterior",
            "es_escena": "on",
        },
    )
    nuevo = next(x for x in backend.admin["lugares"] if x["nombre"] == "terraza")
    assert nuevo["es_escena"] is True


def test_los_argumentos_vacios_de_una_declaracion_se_descartan(navegador, backend):
    """El formulario muestra tres casillas y `posee` lleva dos: la vacía no
    puede llegar como un argumento de más."""
    navegador.post(
        "/admin/casos/caso1/declaraciones/crear",
        data={
            "id": "d9",
            "autor": "bruno_salcedo",
            "tipo": "posee",
            "argumentos": ["victor_cordero", "llave", ""],
        },
    )
    nueva = next(d for d in backend.admin["declaraciones"] if d["id"] == "d9")
    assert nueva["argumentos"] == ["victor_cordero", "llave"]


def test_modificar_una_fila_no_manda_su_clave_en_el_cuerpo(navegador, backend):
    navegador.post(
        "/admin/casos/caso1/personas/editar",
        data={"nombre": "victor_cordero", "rol": "testigo"},
    )
    persona = next(
        p for p in backend.admin["personas"] if p["nombre"] == "victor_cordero"
    )
    assert persona["rol"] == "testigo"


def test_la_baja_de_una_relacion_usa_sus_dos_claves(navegador, backend):
    navegador.post(
        "/admin/casos/caso1/relaciones/eliminar",
        data={"persona": "victor_cordero", "con_quien": "adriana_belmonte"},
    )
    assert backend.admin["relaciones"] == []


def test_la_baja_de_una_oportunidad_viaja_por_query_string(navegador, backend):
    """`visto_en/3` no tiene identificador propio: lo identifica su contenido."""
    navegador.post(
        "/admin/casos/caso1/oportunidades/eliminar",
        data={
            "tipo": "visto_en",
            "persona": "victor_cordero",
            "objeto": "salon_principal",
            "hora": "22",
        },
    )
    assert backend.admin["oportunidades"] == []


def test_un_error_del_backend_se_muestra_y_no_rompe_la_pagina(navegador):
    """El mensaje del backend es el que ve el usuario."""
    respuesta = navegador.post(
        "/admin/casos/caso1/personas/crear",
        data={"nombre": "victor_cordero", "rol": "testigo"},
        follow_redirects=True,
    )
    html = texto(respuesta)
    assert "No se pudo agregar la persona" in html
    assert "ya existe ese registro" in html


def test_crear_un_caso_lleva_a_su_editor(navegador, backend):
    respuesta = navegador.post(
        "/admin/casos",
        data={
            "id": "caso4",
            "titulo": "Caso nuevo",
            "descripcion": "Alta desde la interfaz.",
            "dificultad": "media",
        },
    )
    assert respuesta.status_code == 302
    assert "/admin/casos/caso4" in respuesta.headers["Location"]
    assert "caso4" in backend.casos_creados


def test_eliminar_un_caso_de_fabrica_avisa_que_es_reversible(navegador):
    html = texto(navegador.post("/admin/casos/caso3/eliminar", follow_redirects=True))
    assert "restaurar" in html


def test_el_tablero_lista_los_cambios_y_ofrece_restaurar(navegador):
    navegador.post(
        "/admin/casos/caso1/personas/crear",
        data={"nombre": "nadia_luna", "rol": "testigo"},
    )
    html = texto(navegador.get("/admin"))
    assert "Cambios administrativos" in html
    assert "estado de fábrica" in html


def test_restaurar_informa_cuantas_operaciones_deshizo(navegador, backend):
    navegador.post(
        "/admin/casos/caso1/personas/crear",
        data={"nombre": "nadia_luna", "rol": "testigo"},
    )
    html = texto(navegador.post("/admin/restaurar", follow_redirects=True))
    assert "Se deshicieron 1 operaciones" in html
    assert backend.operaciones == []
