"""Módulo administrativo: CRUD sobre la base de conocimiento.

Lo que la investigación consulta, esto lo edita. Cada recurso se lee de los
`api_admin_*` de logic_detective.pl y se escribe con `assertz`/`retractall` a
través de `administracion`, que además lo persiste.

Se editan hechos, no filas de una tabla: modificar una evidencia es retirar el
hecho que unifica con `evidencia(e1,_,_,_,_)` y afirmar el nuevo. La base de
conocimiento *es* el almacén.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .administracion import administracion
from .comun import atomo, casos_de_ejemplo, consultar, exigir_caso
from .terminos import (
    DIFICULTADES,
    LIBRE,
    MEDIOS,
    ROLES,
    TIPOS_DECLARACION,
    TIPOS_EVIDENCIA,
    TIPOS_MOTIVO,
    TIPOS_OPORTUNIDAD,
    TIPOS_RELACION,
    TIPOS_RESPALDO,
    ValorInvalido,
    hecho,
    hora as valida_hora,
    patron,
    texto,
    uno_de,
)
from .terminos import atomo as valida_atomo

router = APIRouter(prefix="/api/admin", tags=["administración"])


# --------------------------------------------------------------------------
# Integridad referencial
#
# El motor no la exige: `declaracion(d9, fantasma, ...)` se afirma sin protestar
# y después no deduce nada, que es peor que un error porque parece que funciona.
# --------------------------------------------------------------------------


def _hay(caso: str, *patrones: str) -> bool:
    return any(administracion.existe_hecho(caso, p) for p in patrones)


def exigir_persona(caso: str, nombre: str, campo: str) -> str:
    """Valida que la persona esté declarada en el caso, con cualquier rol."""
    nombre = valida_atomo(nombre, campo)
    if not _hay(
        caso,
        hecho("sospechoso", nombre),
        hecho("testigo", nombre),
        hecho("victima", nombre),
    ):
        raise ValorInvalido(campo, f"'{nombre}' no es una persona del caso {caso}")
    return nombre


def exigir_lugar(caso: str, nombre: str, campo: str) -> str:
    nombre = valida_atomo(nombre, campo)
    if not administracion.existe_hecho(caso, patron("lugar", nombre, LIBRE)):
        raise ValorInvalido(campo, f"'{nombre}' no es un lugar del caso {caso}")
    return nombre


def exigir_evidencia(caso: str, id_ev: str, campo: str) -> str:
    id_ev = valida_atomo(id_ev, campo)
    if not administracion.existe_hecho(
        caso, patron("evidencia", id_ev, LIBRE, LIBRE, LIBRE, LIBRE)
    ):
        raise ValorInvalido(campo, f"no existe la evidencia '{id_ev}' en {caso}")
    return id_ev


def exigir_libre(caso: str, patron_clave: str, campo: str, detalle: str) -> None:
    """Rechaza un alta cuyo identificador ya está usado en el caso."""
    if administracion.existe_hecho(caso, patron_clave):
        raise ValorInvalido(campo, detalle)


def exigir_registro(caso: str, patron_clave: str, que: str) -> None:
    """404 si el registro que se quiere modificar o borrar no existe."""
    if not administracion.existe_hecho(caso, patron_clave):
        raise HTTPException(
            status_code=404, detail=f"No existe {que} en el caso {caso}"
        )


def _borrar(caso: str, *patrones: str) -> dict[str, int]:
    """Aplica varias bajas y devuelve cuántos hechos se llevó cada una."""
    resumen: dict[str, int] = {}
    for p in patrones:
        cuantos = administracion.baja(caso, p)
        if cuantos:
            resumen[p.split("(")[0]] = resumen.get(p.split("(")[0], 0) + cuantos
    return resumen


# --------------------------------------------------------------------------
# Cuerpos de las peticiones
# --------------------------------------------------------------------------


class CasoNuevo(BaseModel):
    id: str
    titulo: str
    descripcion: str
    dificultad: str = "media"


class CasoEditado(BaseModel):
    titulo: str
    descripcion: str
    dificultad: str = "media"


class PersonaEntrada(BaseModel):
    nombre: str
    rol: str = "sospechoso"


class PersonaEditada(BaseModel):
    rol: str


class EvidenciaEntrada(BaseModel):
    id: str
    tipo: str
    lugar: str
    hora: Union[int, str] = "desconocida"
    descripcion: str
    incrimina: list[str] = Field(default_factory=list)


class EvidenciaEditada(BaseModel):
    tipo: str
    lugar: str
    hora: Union[int, str] = "desconocida"
    descripcion: str
    incrimina: list[str] = Field(default_factory=list)


class LugarEntrada(BaseModel):
    nombre: str
    descripcion: str
    es_escena: bool = False
    conectado_con: list[str] = Field(default_factory=list)


class LugarEditado(BaseModel):
    descripcion: str
    es_escena: bool = False
    conectado_con: list[str] = Field(default_factory=list)


class DeclaracionEntrada(BaseModel):
    id: str
    autor: str
    tipo: str
    argumentos: list[Union[int, str]]


class DeclaracionEditada(BaseModel):
    autor: str
    tipo: str
    argumentos: list[Union[int, str]]


class RelacionEntrada(BaseModel):
    persona: str
    con_quien: str
    tipo: str


class RelacionEditada(BaseModel):
    tipo: str


class CoartadaEntrada(BaseModel):
    persona: str
    lugar: str
    hora: int
    respaldo: str = "ninguno"
    respaldo_valor: Optional[str] = None


class CoartadaEditada(BaseModel):
    lugar: str
    hora: int
    respaldo: str = "ninguno"
    respaldo_valor: Optional[str] = None


class MotivoEntrada(BaseModel):
    persona: str
    tipo: str


class MotivoEditado(BaseModel):
    tipo: str


class OportunidadEntrada(BaseModel):
    tipo: str
    persona: str
    objeto: str
    hora: Optional[int] = None


class FichaEditada(BaseModel):
    escena: Optional[str] = None
    hora_incidente: Optional[int] = None
    medios_requeridos: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Esquema y estado
# --------------------------------------------------------------------------


@router.get("/esquema")
async def esquema() -> dict[str, Any]:
    """El vocabulario del esquema, para que la interfaz arme sus formularios.

    La interfaz no repite estas listas: las pide acá.
    """
    return {
        "dificultades": list(DIFICULTADES),
        "roles": list(ROLES),
        "tipos_relacion": list(TIPOS_RELACION),
        "tipos_motivo": list(TIPOS_MOTIVO),
        "medios": list(MEDIOS),
        "tipos_evidencia": list(TIPOS_EVIDENCIA),
        "tipos_declaracion": {
            nombre: list(args) for nombre, args in TIPOS_DECLARACION.items()
        },
        "tipos_respaldo": {nombre: arg for nombre, arg in TIPOS_RESPALDO.items()},
        "tipos_oportunidad": {
            nombre: dict(config) for nombre, config in TIPOS_OPORTUNIDAD.items()
        },
    }


@router.get("/historial")
async def historial(limite: int = 50) -> dict[str, Any]:
    """Las últimas operaciones administrativas."""
    return {
        "cambios": administracion.cambios,
        "casos_creados": administracion.casos_creados(),
        "casos_eliminados": administracion.casos_eliminados(),
        "operaciones": administracion.historial(limite),
    }


@router.post("/restaurar")
async def restaurar() -> dict[str, Any]:
    """Deshace todos los cambios administrativos y vuelve al estado de fábrica."""
    deshechas = administracion.restaurar()
    return {"estado": "restaurado", "operaciones_deshechas": deshechas}


# --------------------------------------------------------------------------
# Casos
# --------------------------------------------------------------------------


def _ficha_caso(caso: str) -> dict[str, Any]:
    """Ficha completa de un caso para el módulo administrativo."""
    filas = consultar(
        f"api_caso({caso}, Id, Titulo, Descripcion, Dificultad, Estado, NS, NE, NL, ND)"
    )
    if not filas:
        raise HTTPException(status_code=404, detail=f"El caso '{caso}' no existe")
    fila = filas[0]
    reglas = consultar(f"api_reglas_propias({caso}, N)")
    ficha: dict[str, list[Any]] = {
        "escena_del_incidente": [],
        "hora_del_incidente": [],
        "medio_requerido": [],
    }
    for linea in consultar(f"api_admin_ficha({caso}, Clave, Valor)"):
        ficha.setdefault(linea["Clave"], []).append(linea["Valor"])
    return {
        "id": fila["Id"],
        "titulo": fila["Titulo"],
        "descripcion": fila["Descripcion"],
        "dificultad": fila["Dificultad"],
        "estado": fila["Estado"],
        "es_ejemplo": caso in casos_de_ejemplo(),
        "creado_en_administracion": caso in administracion.casos_creados(),
        "conteos": {
            "sospechosos": fila["NS"],
            "evidencias": fila["NE"],
            "lugares": fila["NL"],
            "declaraciones": fila["ND"],
            "reglas_de_inferencia": reglas[0]["N"] if reglas else None,
        },
        "ficha": ficha,
    }


@router.get("/casos")
async def listar_casos_admin() -> list[dict[str, Any]]:
    """Todos los casos del catálogo, con sus conteos y su ficha."""
    return [_ficha_caso(fila["M"]) for fila in consultar("caso_modulo(M)")]


@router.get("/casos/{caso_id}")
async def obtener_caso_admin(caso_id: str) -> dict[str, Any]:
    return _ficha_caso(exigir_caso(caso_id))


@router.post("/casos", status_code=201)
async def crear_caso(cuerpo: CasoNuevo) -> dict[str, Any]:
    """Da de alta un caso con su propio módulo de Prolog.

    Hereda las reglas compartidas de reglas_base.pl, así que deduce desde el
    primer hecho. Lo que no tiene son reglas propias, y por eso `estado_caso/3`
    lo reporta incompleto.
    """
    identificador = valida_atomo(cuerpo.id, "id")
    if consultar(f"caso_modulo({identificador})"):
        raise ValorInvalido("id", f"ya existe un caso llamado '{identificador}'")
    dificultad = uno_de(cuerpo.dificultad, "dificultad", DIFICULTADES)
    texto(cuerpo.titulo, "titulo", largo=120)
    texto(cuerpo.descripcion, "descripcion")
    administracion.crear_caso(
        identificador, cuerpo.titulo.strip(), cuerpo.descripcion.strip(), dificultad
    )
    return _ficha_caso(identificador)


@router.put("/casos/{caso_id}")
async def modificar_caso(caso_id: str, cuerpo: CasoEditado) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    dificultad = uno_de(cuerpo.dificultad, "dificultad", DIFICULTADES)
    texto(cuerpo.titulo, "titulo", largo=120)
    texto(cuerpo.descripcion, "descripcion")
    administracion.modificar_caso(
        caso, cuerpo.titulo.strip(), cuerpo.descripcion.strip(), dificultad
    )
    return _ficha_caso(caso)


@router.delete("/casos/{caso_id}")
async def eliminar_caso(caso_id: str) -> dict[str, Any]:
    """Saca el caso del catálogo."""
    caso = exigir_caso(caso_id)
    de_administracion = caso in administracion.casos_creados()
    administracion.eliminar_caso(caso)
    return {
        "eliminado": caso,
        "definitivo": de_administracion,
        "reversible_con_restaurar": True,
    }


@router.put("/casos/{caso_id}/ficha")
async def modificar_ficha(caso_id: str, cuerpo: FichaEditada) -> dict[str, Any]:
    """Fija la escena, la hora del incidente y los medios que exigió.

    Sin `escena_del_incidente/1` nadie tuvo oportunidad, y sin
    `medio_requerido/1` nadie tuvo capacidad.
    """
    caso = exigir_caso(caso_id)
    if cuerpo.escena is not None:
        escena = exigir_lugar(caso, cuerpo.escena, "escena")
        administracion.baja(caso, patron("escena_del_incidente", LIBRE))
        administracion.alta(caso, hecho("escena_del_incidente", escena))
    if cuerpo.hora_incidente is not None:
        hora = valida_hora(cuerpo.hora_incidente, "hora_incidente")
        administracion.baja(caso, patron("hora_del_incidente", LIBRE))
        administracion.alta(caso, hecho("hora_del_incidente", hora))
    medios = [uno_de(m, "medios_requeridos", MEDIOS) for m in cuerpo.medios_requeridos]
    if medios:
        administracion.baja(caso, patron("medio_requerido", LIBRE))
        for medio in medios:
            administracion.alta(caso, hecho("medio_requerido", medio))
    return _ficha_caso(caso)


# --------------------------------------------------------------------------
# Personas: sospechosos, testigos y víctima
# --------------------------------------------------------------------------


def _patrones_de_persona(nombre: str) -> tuple[str, ...]:
    """Todo lo que deja de tener sentido si la persona sale del caso.

    Una relación con alguien que no existe o el motivo de un ausente no son
    datos incompletos: son datos falsos, y el motor deduciría con ellos.
    """
    return (
        hecho("sospechoso", nombre),
        hecho("testigo", nombre),
        hecho("victima", nombre),
        patron("relacion", nombre, LIBRE, LIBRE),
        patron("relacion", LIBRE, nombre, LIBRE),
        patron("motivo", nombre, LIBRE),
        patron("coartada", nombre, LIBRE, LIBRE, LIBRE),
        patron("coartada", LIBRE, LIBRE, LIBRE, hecho("testigo", nombre)),
        patron("declaracion", LIBRE, nombre, LIBRE),
        patron("evidencia_incrimina", LIBRE, nombre),
        patron("visto_en", nombre, LIBRE, LIBRE),
        patron("registro_acceso", nombre, LIBRE, LIBRE),
        patron("tiene_llave", nombre, LIBRE),
        patron("autorizado_en", nombre, LIBRE),
        patron("posee_medio", nombre, LIBRE),
    )


@router.get("/casos/{caso_id}/personas")
async def listar_personas(caso_id: str) -> list[dict[str, Any]]:
    caso = exigir_caso(caso_id)
    return [
        {"nombre": fila["Persona"], "rol": fila["Rol"]}
        for fila in consultar(f"api_admin_persona({caso}, Persona, Rol)")
    ]


@router.post("/casos/{caso_id}/personas", status_code=201)
async def crear_persona(caso_id: str, cuerpo: PersonaEntrada) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    nombre = valida_atomo(cuerpo.nombre, "nombre")
    rol = uno_de(cuerpo.rol, "rol", ROLES)
    if _hay(
        caso,
        hecho("sospechoso", nombre),
        hecho("testigo", nombre),
        hecho("victima", nombre),
    ):
        raise ValorInvalido("nombre", f"'{nombre}' ya está en el caso {caso}")
    administracion.alta(caso, hecho(rol, nombre))
    return {"nombre": nombre, "rol": rol}


@router.put("/casos/{caso_id}/personas/{nombre}")
async def modificar_persona(
    caso_id: str, nombre: str, cuerpo: PersonaEditada
) -> dict[str, Any]:
    """Cambia el rol de una persona sin tocar lo que cuelga de ella.

    Pasar un testigo a sospechoso lo mete en el ranking y le exige coartada.
    """
    caso = exigir_caso(caso_id)
    persona = exigir_persona(caso, nombre, "nombre")
    rol = uno_de(cuerpo.rol, "rol", ROLES)
    for anterior in ROLES:
        administracion.baja(caso, hecho(anterior, persona))
    administracion.alta(caso, hecho(rol, persona))
    return {"nombre": persona, "rol": rol}


@router.delete("/casos/{caso_id}/personas/{nombre}")
async def eliminar_persona(caso_id: str, nombre: str) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    persona = exigir_persona(caso, nombre, "nombre")
    return {
        "eliminada": persona,
        "en_cascada": _borrar(caso, *_patrones_de_persona(persona)),
    }


# --------------------------------------------------------------------------
# Evidencias
# --------------------------------------------------------------------------


def _escribir_evidencia(
    caso: str,
    id_ev: str,
    tipo: str,
    lugar: str,
    hora: Union[int, str],
    descripcion: str,
    incrimina: list[str],
) -> dict[str, Any]:
    """Valida y afirma una evidencia con sus incriminaciones.

    Valida todo antes de escribir nada: si el último incriminado no existe, no
    debe quedar una evidencia a medio registrar.
    """
    tipo_ev = uno_de(tipo, "tipo", TIPOS_EVIDENCIA)
    lugar_ev = exigir_lugar(caso, lugar, "lugar")
    hora_ev = valida_hora(hora, "hora", permite_desconocida=True)
    descripcion_ev = texto(descripcion, "descripcion")
    personas = [exigir_persona(caso, p, "incrimina") for p in dict.fromkeys(incrimina)]
    administracion.baja(caso, patron("evidencia_incrimina", id_ev, LIBRE))
    administracion.reemplazar(
        caso,
        patron("evidencia", id_ev, LIBRE, LIBRE, LIBRE, LIBRE),
        hecho("evidencia", id_ev, tipo_ev, lugar_ev, hora_ev, descripcion_ev),
    )
    for persona in personas:
        administracion.alta(caso, hecho("evidencia_incrimina", id_ev, persona))
    return {
        "id": id_ev,
        "tipo": tipo_ev,
        "lugar": lugar_ev,
        "hora": hora_ev,
        "incrimina": personas,
    }


@router.get("/casos/{caso_id}/evidencias")
async def listar_evidencias_admin(caso_id: str) -> list[dict[str, Any]]:
    caso = exigir_caso(caso_id)
    incriminaciones: dict[str, list[str]] = {}
    for fila in consultar(f"api_evidencia_incrimina({caso}, IdEv, Persona)"):
        incriminaciones.setdefault(fila["IdEv"], []).append(fila["Persona"])
    return [
        {
            "id": fila["Id"],
            "tipo": fila["Tipo"],
            "lugar": fila["Lugar"],
            "hora": fila["Hora"],
            "descripcion": fila["Descripcion"],
            "incrimina": incriminaciones.get(fila["Id"], []),
        }
        for fila in consultar(
            f"api_admin_evidencia({caso}, Id, Tipo, Lugar, Hora, Descripcion)"
        )
    ]


@router.post("/casos/{caso_id}/evidencias", status_code=201)
async def crear_evidencia(caso_id: str, cuerpo: EvidenciaEntrada) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    id_ev = valida_atomo(cuerpo.id, "id")
    exigir_libre(
        caso,
        patron("evidencia", id_ev, LIBRE, LIBRE, LIBRE, LIBRE),
        "id",
        f"ya existe una evidencia '{id_ev}' en {caso}",
    )
    return _escribir_evidencia(
        caso,
        id_ev,
        cuerpo.tipo,
        cuerpo.lugar,
        cuerpo.hora,
        cuerpo.descripcion,
        cuerpo.incrimina,
    )


@router.put("/casos/{caso_id}/evidencias/{id_ev}")
async def modificar_evidencia(
    caso_id: str, id_ev: str, cuerpo: EvidenciaEditada
) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clave = atomo(id_ev, "id")
    exigir_registro(
        caso,
        patron("evidencia", clave, LIBRE, LIBRE, LIBRE, LIBRE),
        f"la evidencia '{clave}'",
    )
    return _escribir_evidencia(
        caso,
        clave,
        cuerpo.tipo,
        cuerpo.lugar,
        cuerpo.hora,
        cuerpo.descripcion,
        cuerpo.incrimina,
    )


@router.delete("/casos/{caso_id}/evidencias/{id_ev}")
async def eliminar_evidencia(caso_id: str, id_ev: str) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clave = atomo(id_ev, "id")
    exigir_registro(
        caso,
        patron("evidencia", clave, LIBRE, LIBRE, LIBRE, LIBRE),
        f"la evidencia '{clave}'",
    )
    return {
        "eliminada": clave,
        "en_cascada": _borrar(
            caso,
            patron("evidencia", clave, LIBRE, LIBRE, LIBRE, LIBRE),
            patron("evidencia_incrimina", clave, LIBRE),
        ),
    }


# --------------------------------------------------------------------------
# Lugares
# --------------------------------------------------------------------------


@router.get("/casos/{caso_id}/lugares")
async def listar_lugares_admin(caso_id: str) -> list[dict[str, Any]]:
    caso = exigir_caso(caso_id)
    conexiones: dict[str, list[str]] = {}
    for fila in consultar(f"api_admin_conexion({caso}, Desde, Hasta)"):
        conexiones.setdefault(fila["Desde"], []).append(fila["Hasta"])
    escenas = {
        fila["Valor"]
        for fila in consultar(f"api_admin_ficha({caso}, escena_del_incidente, Valor)")
    }
    return [
        {
            "nombre": fila["Nombre"],
            "descripcion": fila["Descripcion"],
            "es_escena": fila["Nombre"] in escenas,
            "conectado_con": conexiones.get(fila["Nombre"], []),
        }
        for fila in consultar(f"api_admin_lugar({caso}, Nombre, Descripcion)")
    ]


def _escribir_lugar(
    caso: str, nombre: str, descripcion: str, es_escena: bool, conectado_con: list[str]
) -> dict[str, Any]:
    descripcion_lugar = texto(descripcion, "descripcion")
    vecinos = []
    for vecino in dict.fromkeys(conectado_con):
        destino = valida_atomo(vecino, "conectado_con")
        if destino == nombre:
            raise ValorInvalido("conectado_con", "un lugar no se conecta consigo mismo")
        vecinos.append(exigir_lugar(caso, destino, "conectado_con"))
    # Recién acá se escribe: una conexión rota no debe dejar el lugar a medias.
    administracion.reemplazar(
        caso,
        patron("lugar", nombre, LIBRE),
        hecho("lugar", nombre, descripcion_lugar),
    )
    administracion.baja(caso, patron("lugar_conectado", nombre, LIBRE))
    for destino in vecinos:
        administracion.alta(caso, hecho("lugar_conectado", nombre, destino))
    if es_escena:
        administracion.baja(caso, patron("escena_del_incidente", LIBRE))
        administracion.alta(caso, hecho("escena_del_incidente", nombre))
    else:
        administracion.baja(caso, hecho("escena_del_incidente", nombre))
    return {
        "nombre": nombre,
        "es_escena": es_escena,
        "conectado_con": vecinos,
    }


@router.post("/casos/{caso_id}/lugares", status_code=201)
async def crear_lugar(caso_id: str, cuerpo: LugarEntrada) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    nombre = valida_atomo(cuerpo.nombre, "nombre")
    exigir_libre(
        caso,
        patron("lugar", nombre, LIBRE),
        "nombre",
        f"ya existe un lugar '{nombre}' en {caso}",
    )
    return _escribir_lugar(
        caso, nombre, cuerpo.descripcion, cuerpo.es_escena, cuerpo.conectado_con
    )


@router.put("/casos/{caso_id}/lugares/{nombre}")
async def modificar_lugar(
    caso_id: str, nombre: str, cuerpo: LugarEditado
) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clave = atomo(nombre, "nombre")
    exigir_registro(caso, patron("lugar", clave, LIBRE), f"el lugar '{clave}'")
    return _escribir_lugar(
        caso, clave, cuerpo.descripcion, cuerpo.es_escena, cuerpo.conectado_con
    )


@router.delete("/casos/{caso_id}/lugares/{nombre}")
async def eliminar_lugar(caso_id: str, nombre: str) -> dict[str, Any]:
    """Borra el lugar y todo lo que lo ubicaba, evidencias incluidas."""
    caso = exigir_caso(caso_id)
    clave = atomo(nombre, "nombre")
    exigir_registro(caso, patron("lugar", clave, LIBRE), f"el lugar '{clave}'")
    return {
        "eliminado": clave,
        "en_cascada": _borrar(
            caso,
            patron("lugar", clave, LIBRE),
            hecho("escena_del_incidente", clave),
            patron("lugar_conectado", clave, LIBRE),
            patron("lugar_conectado", LIBRE, clave),
            patron("evidencia", LIBRE, LIBRE, clave, LIBRE, LIBRE),
            patron("visto_en", LIBRE, clave, LIBRE),
            patron("registro_acceso", LIBRE, clave, LIBRE),
            patron("tiene_llave", LIBRE, clave),
            patron("autorizado_en", LIBRE, clave),
            patron("coartada", LIBRE, clave, LIBRE, LIBRE),
        ),
    }


# --------------------------------------------------------------------------
# Declaraciones
# --------------------------------------------------------------------------


def _contenido_declaracion(caso: str, tipo: str, argumentos: list[Any]) -> str:
    """Arma el término de una declaración validando argumento por argumento.

    El funtor sale de `TIPOS_DECLARACION`: con cualquier otro, la declaración se
    afirmaría sin error y no contradiría nunca nada.
    """
    funtor = uno_de(tipo, "tipo", TIPOS_DECLARACION)
    esperados = TIPOS_DECLARACION[funtor]
    if len(argumentos) != len(esperados):
        raise ValorInvalido(
            "argumentos",
            f"'{funtor}' lleva {len(esperados)} argumentos ({', '.join(esperados)}), "
            f"llegaron {len(argumentos)}",
        )
    escritos = []
    for valor, clase in zip(argumentos, esperados):
        if clase == "persona":
            escritos.append(exigir_persona(caso, str(valor), "argumentos"))
        elif clase == "lugar":
            escritos.append(exigir_lugar(caso, str(valor), "argumentos"))
        elif clase == "hora":
            escritos.append(valida_hora(valor, "argumentos"))
        else:
            escritos.append(uno_de(str(valor), "argumentos", MEDIOS))
    return hecho(funtor, *escritos)


@router.get("/casos/{caso_id}/declaraciones")
async def listar_declaraciones_admin(caso_id: str) -> list[dict[str, Any]]:
    caso = exigir_caso(caso_id)
    return [
        {
            "id": fila["Id"],
            "autor": fila["Autor"],
            "tipo": fila["Funtor"],
            "contenido": fila["Contenido"],
        }
        for fila in consultar(
            f"api_admin_declaracion({caso}, Id, Autor, Funtor, Contenido)"
        )
    ]


@router.post("/casos/{caso_id}/declaraciones", status_code=201)
async def crear_declaracion(caso_id: str, cuerpo: DeclaracionEntrada) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    id_decl = valida_atomo(cuerpo.id, "id")
    exigir_libre(
        caso,
        patron("declaracion", id_decl, LIBRE, LIBRE),
        "id",
        f"ya existe una declaración '{id_decl}' en {caso}",
    )
    autor = exigir_persona(caso, cuerpo.autor, "autor")
    contenido = _contenido_declaracion(caso, cuerpo.tipo, cuerpo.argumentos)
    administracion.alta(caso, hecho("declaracion", id_decl, autor, contenido))
    return {"id": id_decl, "autor": autor, "contenido": contenido}


@router.put("/casos/{caso_id}/declaraciones/{id_decl}")
async def modificar_declaracion(
    caso_id: str, id_decl: str, cuerpo: DeclaracionEditada
) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clave = atomo(id_decl, "id")
    exigir_registro(
        caso, patron("declaracion", clave, LIBRE, LIBRE), f"la declaración '{clave}'"
    )
    autor = exigir_persona(caso, cuerpo.autor, "autor")
    contenido = _contenido_declaracion(caso, cuerpo.tipo, cuerpo.argumentos)
    administracion.reemplazar(
        caso,
        patron("declaracion", clave, LIBRE, LIBRE),
        hecho("declaracion", clave, autor, contenido),
    )
    return {"id": clave, "autor": autor, "contenido": contenido}


@router.delete("/casos/{caso_id}/declaraciones/{id_decl}")
async def eliminar_declaracion(caso_id: str, id_decl: str) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clave = atomo(id_decl, "id")
    exigir_registro(
        caso, patron("declaracion", clave, LIBRE, LIBRE), f"la declaración '{clave}'"
    )
    administracion.baja(caso, patron("declaracion", clave, LIBRE, LIBRE))
    return {"eliminada": clave}


# --------------------------------------------------------------------------
# Relaciones
# --------------------------------------------------------------------------


@router.get("/casos/{caso_id}/relaciones")
async def listar_relaciones_admin(caso_id: str) -> list[dict[str, Any]]:
    caso = exigir_caso(caso_id)
    return [
        {
            "persona": fila["Persona"],
            "con_quien": fila["ConQuien"],
            "tipo": fila["Tipo"],
        }
        for fila in consultar(f"api_admin_relacion({caso}, Persona, ConQuien, Tipo)")
    ]


@router.post("/casos/{caso_id}/relaciones", status_code=201)
async def crear_relacion(caso_id: str, cuerpo: RelacionEntrada) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    persona = exigir_persona(caso, cuerpo.persona, "persona")
    con_quien = exigir_persona(caso, cuerpo.con_quien, "con_quien")
    if persona == con_quien:
        raise ValorInvalido("con_quien", "una persona no se relaciona consigo misma")
    tipo = uno_de(cuerpo.tipo, "tipo", TIPOS_RELACION)
    exigir_libre(
        caso,
        patron("relacion", persona, con_quien, LIBRE),
        "con_quien",
        f"ya hay una relación de {persona} con {con_quien}",
    )
    administracion.alta(caso, hecho("relacion", persona, con_quien, tipo))
    return {"persona": persona, "con_quien": con_quien, "tipo": tipo}


@router.put("/casos/{caso_id}/relaciones/{persona}/{con_quien}")
async def modificar_relacion(
    caso_id: str, persona: str, con_quien: str, cuerpo: RelacionEditada
) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    origen = atomo(persona, "persona")
    destino = atomo(con_quien, "con_quien")
    exigir_registro(
        caso,
        patron("relacion", origen, destino, LIBRE),
        f"la relación de '{origen}' con '{destino}'",
    )
    tipo = uno_de(cuerpo.tipo, "tipo", TIPOS_RELACION)
    administracion.reemplazar(
        caso,
        patron("relacion", origen, destino, LIBRE),
        hecho("relacion", origen, destino, tipo),
    )
    return {"persona": origen, "con_quien": destino, "tipo": tipo}


@router.delete("/casos/{caso_id}/relaciones/{persona}/{con_quien}")
async def eliminar_relacion(
    caso_id: str, persona: str, con_quien: str
) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    origen = atomo(persona, "persona")
    destino = atomo(con_quien, "con_quien")
    exigir_registro(
        caso,
        patron("relacion", origen, destino, LIBRE),
        f"la relación de '{origen}' con '{destino}'",
    )
    administracion.baja(caso, patron("relacion", origen, destino, LIBRE))
    return {"eliminada": f"{origen} -> {destino}"}


# --------------------------------------------------------------------------
# Coartadas
# --------------------------------------------------------------------------


def _respaldo(caso: str, tipo: str, valor: Optional[str]) -> str:
    """Arma el término de respaldo de una coartada.

    De esto depende que sirva: `respaldo_confiable/1` exige que el testigo no
    sea sospechoso, que la cámara esté en un lugar del caso y que el documento
    sea una evidencia registrada.
    """
    clase = uno_de(tipo, "respaldo", TIPOS_RESPALDO)
    esperado = TIPOS_RESPALDO[clase]
    if esperado is None:
        return clase
    if valor is None or not str(valor).strip():
        raise ValorInvalido("respaldo_valor", f"'{clase}' necesita un {esperado}")
    if esperado == "persona":
        return hecho(clase, exigir_persona(caso, valor, "respaldo_valor"))
    if esperado == "lugar":
        return hecho(clase, exigir_lugar(caso, valor, "respaldo_valor"))
    return hecho(clase, exigir_evidencia(caso, valor, "respaldo_valor"))


@router.get("/casos/{caso_id}/coartadas")
async def listar_coartadas_admin(caso_id: str) -> list[dict[str, Any]]:
    """El hecho `coartada/4` editable, junto al veredicto que el motor le da."""
    caso = exigir_caso(caso_id)
    evaluadas = {
        fila["Persona"]: {"estado": fila["Estado"], "detalle": fila["Detalle"]}
        for fila in consultar(f"api_coartada({caso}, Persona, Estado, Detalle)")
    }
    return [
        {
            "persona": fila["Persona"],
            "lugar": fila["Lugar"],
            "hora": fila["Hora"],
            "respaldo": fila["Respaldo"],
            "veredicto": evaluadas.get(fila["Persona"]),
        }
        for fila in consultar(
            f"api_admin_coartada({caso}, Persona, Lugar, Hora, Respaldo)"
        )
    ]


@router.post("/casos/{caso_id}/coartadas", status_code=201)
async def crear_coartada(caso_id: str, cuerpo: CoartadaEntrada) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    persona = exigir_persona(caso, cuerpo.persona, "persona")
    exigir_libre(
        caso,
        patron("coartada", persona, LIBRE, LIBRE, LIBRE),
        "persona",
        f"{persona} ya tiene una coartada registrada",
    )
    lugar = exigir_lugar(caso, cuerpo.lugar, "lugar")
    hora = valida_hora(cuerpo.hora, "hora")
    respaldo = _respaldo(caso, cuerpo.respaldo, cuerpo.respaldo_valor)
    administracion.alta(caso, hecho("coartada", persona, lugar, hora, respaldo))
    return {"persona": persona, "lugar": lugar, "hora": hora, "respaldo": respaldo}


@router.put("/casos/{caso_id}/coartadas/{persona}")
async def modificar_coartada(
    caso_id: str, persona: str, cuerpo: CoartadaEditada
) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clave = atomo(persona, "persona")
    exigir_registro(
        caso,
        patron("coartada", clave, LIBRE, LIBRE, LIBRE),
        f"una coartada de '{clave}'",
    )
    lugar = exigir_lugar(caso, cuerpo.lugar, "lugar")
    hora = valida_hora(cuerpo.hora, "hora")
    respaldo = _respaldo(caso, cuerpo.respaldo, cuerpo.respaldo_valor)
    administracion.reemplazar(
        caso,
        patron("coartada", clave, LIBRE, LIBRE, LIBRE),
        hecho("coartada", clave, lugar, hora, respaldo),
    )
    return {"persona": clave, "lugar": lugar, "hora": hora, "respaldo": respaldo}


@router.delete("/casos/{caso_id}/coartadas/{persona}")
async def eliminar_coartada(caso_id: str, persona: str) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clave = atomo(persona, "persona")
    exigir_registro(
        caso,
        patron("coartada", clave, LIBRE, LIBRE, LIBRE),
        f"una coartada de '{clave}'",
    )
    administracion.baja(caso, patron("coartada", clave, LIBRE, LIBRE, LIBRE))
    return {"eliminada": clave}


# --------------------------------------------------------------------------
# Motivos
# --------------------------------------------------------------------------


@router.get("/casos/{caso_id}/motivos")
async def listar_motivos_admin(caso_id: str) -> list[dict[str, Any]]:
    """Los motivos declarados, no los deducidos.

    Solo se puede borrar lo que alguien escribió; un motivo derivado de una
    relación conflictiva se quita cambiando la relación.
    """
    caso = exigir_caso(caso_id)
    return [
        {"persona": fila["Persona"], "tipo": fila["Tipo"]}
        for fila in consultar(f"api_admin_motivo({caso}, Persona, Tipo)")
    ]


@router.post("/casos/{caso_id}/motivos", status_code=201)
async def crear_motivo(caso_id: str, cuerpo: MotivoEntrada) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    persona = exigir_persona(caso, cuerpo.persona, "persona")
    tipo = uno_de(cuerpo.tipo, "tipo", TIPOS_MOTIVO)
    exigir_libre(
        caso,
        hecho("motivo", persona, tipo),
        "tipo",
        f"{persona} ya tiene registrado el motivo '{tipo}'",
    )
    administracion.alta(caso, hecho("motivo", persona, tipo))
    return {"persona": persona, "tipo": tipo}


@router.put("/casos/{caso_id}/motivos/{persona}/{tipo}")
async def modificar_motivo(
    caso_id: str, persona: str, tipo: str, cuerpo: MotivoEditado
) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clave = atomo(persona, "persona")
    anterior = atomo(tipo, "tipo")
    exigir_registro(
        caso, hecho("motivo", clave, anterior), f"el motivo '{anterior}' de '{clave}'"
    )
    nuevo = uno_de(cuerpo.tipo, "tipo", TIPOS_MOTIVO)
    administracion.reemplazar(
        caso, hecho("motivo", clave, anterior), hecho("motivo", clave, nuevo)
    )
    return {"persona": clave, "tipo": nuevo}


@router.delete("/casos/{caso_id}/motivos/{persona}/{tipo}")
async def eliminar_motivo(caso_id: str, persona: str, tipo: str) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clave = atomo(persona, "persona")
    valor = atomo(tipo, "tipo")
    exigir_registro(
        caso, hecho("motivo", clave, valor), f"el motivo '{valor}' de '{clave}'"
    )
    administracion.baja(caso, hecho("motivo", clave, valor))
    return {"eliminado": f"{clave}: {valor}"}


# --------------------------------------------------------------------------
# Oportunidades
# --------------------------------------------------------------------------


def _termino_oportunidad(
    caso: str, tipo: str, persona_valor: str, objeto_valor: str, hora_valor: Any
) -> tuple[str, str, str, str, Optional[str]]:
    """Valida una oportunidad y devuelve su tipo, sus partes y el término."""
    clase = uno_de(tipo, "tipo", TIPOS_OPORTUNIDAD)
    config = TIPOS_OPORTUNIDAD[clase]
    persona = exigir_persona(caso, persona_valor, "persona")
    if config["objeto"] == "lugar":
        objeto = exigir_lugar(caso, objeto_valor, "objeto")
    else:
        objeto = uno_de(objeto_valor, "objeto", MEDIOS)
    if config["hora"]:
        if hora_valor is None:
            raise ValorInvalido("hora", f"'{clase}' necesita una hora")
        hora = valida_hora(hora_valor, "hora")
        return clase, persona, objeto, hecho(clase, persona, objeto, hora), hora
    return clase, persona, objeto, hecho(clase, persona, objeto), None


@router.get("/casos/{caso_id}/oportunidades")
async def listar_oportunidades_admin(caso_id: str) -> list[dict[str, Any]]:
    """Los cinco hechos con los que el motor deduce oportunidad y capacidad."""
    caso = exigir_caso(caso_id)
    return [
        {
            "tipo": fila["Tipo"],
            "persona": fila["Persona"],
            "objeto": fila["Objeto"],
            "hora": None if fila["Hora"] == "sin_hora" else fila["Hora"],
        }
        for fila in consultar(
            f"api_admin_oportunidad({caso}, Tipo, Persona, Objeto, Hora)"
        )
    ]


@router.post("/casos/{caso_id}/oportunidades", status_code=201)
async def crear_oportunidad(caso_id: str, cuerpo: OportunidadEntrada) -> dict[str, Any]:
    caso = exigir_caso(caso_id)
    clase, persona, objeto, termino, hora = _termino_oportunidad(
        caso, cuerpo.tipo, cuerpo.persona, cuerpo.objeto, cuerpo.hora
    )
    exigir_libre(
        caso, termino, "tipo", f"ese hecho de '{clase}' ya está registrado en {caso}"
    )
    administracion.alta(caso, termino)
    return {"tipo": clase, "persona": persona, "objeto": objeto, "hora": hora}


@router.delete("/casos/{caso_id}/oportunidades")
async def eliminar_oportunidad(
    caso_id: str, tipo: str, persona: str, objeto: str, hora: Optional[int] = None
) -> dict[str, Any]:
    """Borra una oportunidad.

    La clave va por query string porque `visto_en/3` no tiene identificador
    propio: lo identifica su contenido completo.
    """
    caso = exigir_caso(caso_id)
    clase, nombre, valor, termino, _ = _termino_oportunidad(
        caso, tipo, persona, objeto, hora
    )
    exigir_registro(caso, termino, f"el hecho '{termino}'")
    administracion.baja(caso, termino)
    return {"eliminado": termino}
