# Arquitectura del sistema

**Proyecto 1 — Logic Detective** · Inteligencia Artificial 1 · Sección A · Grupo 15
Facultad de Ingeniería, USAC · Segundo semestre 2026

Diagramas arquitectónicos y de flujo del sistema. La guía de instalación y la
referencia de la API están en [`MANUAL_TECNICO.md`](MANUAL_TECNICO.md).

> Los diagramas están escritos en Mermaid. GitHub los renderiza directamente al
> abrir este archivo; no hay imágenes sueltas que se puedan desincronizar del
> código.

---

## 1. Vista de componentes

Tres componentes y dos protocolos. El motor de inferencia **no es un servicio
aparte**: SWI-Prolog se carga dentro del proceso del backend a través de PySwip,
que enlaza `libswipl` por FFI.

```mermaid
graph LR
    U["Usuario<br/>rol de detective"]

    subgraph FE["Contenedor frontend · puerto 8080"]
        F["Flask + Jinja2<br/>app.py"]
        T["Plantillas<br/>base · inicio · investigacion · caso<br/>informe · admin · admin_caso"]
        S["estilos.css"]
    end

    subgraph BE["Contenedor backend · puerto 8000"]
        A["FastAPI · main.py<br/>módulo de investigación"]
        AD["admin_api.py<br/>módulo administrativo"]
        TE["terminos.py<br/>validación y escritura<br/>de términos"]
        AL["administracion.py<br/>bitácora de cambios"]
        M["MotorProlog<br/>prolog_engine.py"]
    end

    subgraph PL["SWI-Prolog · dentro del proceso del backend"]
        L["logic_detective.pl<br/>cargador y fachada api_*"]
        R["reglas_base.pl<br/>reglas de inferencia"]
        K["caso1 · caso2 · caso3 · caso_demo<br/>hechos de cada caso"]
    end

    D[("datos/administracion.json<br/>volumen")]

    U -->|HTTP| F
    F --> T
    T --> S
    F -->|"HTTP · JSON"| A
    F -->|"HTTP · JSON"| AD
    A -->|"lee: filas()"| M
    AD --> TE
    AD --> AL
    AL -->|"escribe: afirmar() / retirar()"| M
    AL <-->|"persiste y reaplica"| D
    M -->|"PySwip · FFI"| L
    L --> R
    L --> K
    R -.->|"include/1"| K
```

Los dos módulos comparten el mismo motor cargado en memoria: la investigación lo
consulta y la administración lo escribe. Eso es lo que hace que un alta se vea en
la consulta siguiente, sin sincronizar nada y sin una segunda copia de los datos.

| Componente | Tecnología | Responsabilidad | Qué **no** hace |
| --- | --- | --- | --- |
| frontend | Flask 3.1 + Jinja2 | Presentar y recoger acciones del usuario | No razona ni guarda estado |
| backend | FastAPI + PySwip | Validar entradas, armar metas Prolog, serializar | No decide nada del dominio |
| administración | FastAPI + JSON | Editar los hechos del motor y persistir los cambios | No escribe reglas: eso sigue siendo trabajo de un `.pl` |
| motor | SWI-Prolog 9 | **Toda** la deducción | No presenta ni valida HTTP |

**Regla de diseño que atraviesa el proyecto:** toda deducción ocurre en Prolog.
Si aparece un `if` en Python que decide quién es culpable, esa lógica está en el
lugar equivocado.

---

## 2. Flujo de una consulta

Recorrido completo de `GET /investigacion/caso_demo`, desde el clic hasta el
HTML. Muestra dónde ocurre la validación, dónde el candado y dónde la inferencia.

```mermaid
sequenceDiagram
    actor U as Usuario
    participant F as Flask<br/>:8080
    participant A as FastAPI<br/>:8000
    participant M as MotorProlog
    participant P as SWI-Prolog

    U->>F: GET /investigacion/caso_demo
    F->>A: GET /api/casos/caso_demo
    A->>A: exigir_caso: valida que sea un atomo
    A->>M: filas("api_caso(caso_demo, ...)")
    M->>M: toma el candado
    M->>P: query por FFI
    P->>P: unificacion y backtracking<br/>sobre reglas_base + hechos
    P-->>M: una solucion por fila
    M-->>A: lista de diccionarios de Python
    A-->>F: JSON

    Note over F,A: la vista pide en paralelo el resto de secciones
    F->>A: /sospechosos /evidencias /coartadas<br/>/contradicciones /conclusion ...
    A-->>F: JSON

    F->>F: Jinja2 renderiza caso.html
    F-->>U: HTML
```

Puntos que conviene retener:

1. **La validación ocurre antes de tocar Prolog.** Las metas se arman
   concatenando texto, así que todo lo que venga del cliente pasa por `atomo()`.
2. **Una sola consulta a la vez.** `MotorProlog` serializa con un candado porque
   SWI-Prolog no es seguro para llamadas concurrentes desde varios hilos.
3. **Una lista vacía no es un error.** Un caso todavía sin hechos responde `200`
   con `[]`; es una respuesta válida en lógica.

### 2.1 Flujo de una escritura administrativa

El camino inverso: `POST /api/admin/casos/caso1/motivos`. Muestra dónde se
valida, dónde se persiste y en qué momento el cambio queda visible para la
investigación.

```mermaid
sequenceDiagram
    actor U as Administrador
    participant F as Flask<br/>:8080
    participant AD as admin_api.py
    participant TE as terminos.py
    participant AL as administracion.py
    participant M as MotorProlog
    participant P as SWI-Prolog
    participant D as administracion.json

    U->>F: POST /admin/casos/caso1/motivos/crear
    F->>AD: POST /api/admin/casos/caso1/motivos
    AD->>TE: uno_de(tipo, TIPOS_MOTIVO)
    TE-->>AD: "dinero"
    AD->>M: ¿existe sospechoso(valeria_montes)?
    M-->>AD: sí
    Note over AD: integridad referencial:<br/>el motor aceptaria un fantasma<br/>y despues no deduciria nada
    AD->>TE: hecho("motivo", persona, tipo)
    TE-->>AD: "motivo(valeria_montes,dinero)"
    AD->>AL: alta(caso1, termino)
    AL->>M: afirmar(caso1, termino)
    M->>P: assertz(caso1:(motivo(valeria_montes,dinero)))
    AL->>D: escribe la bitacora (temporal + rename)
    AL-->>AD: listo
    AD-->>F: 201
    F-->>U: redirect + mensaje

    Note over P: desde aca, GET /api/casos/caso1/motivos<br/>ya devuelve el motivo nuevo
```

Si algo falla en la validación, no se escribió nada: el término se arma entero
—y con él se comprueban todas sus referencias— **antes** del primer `assertz`.

Al arrancar, `administracion.py` vuelve a aplicar esa bitácora sobre el motor
recién cargado. Es lo que hace que los cambios sobrevivan a un reinicio sin
tocar los archivos `.pl` de fábrica:

```mermaid
graph LR
    PL["archivos .pl<br/>estado de fabrica"] --> MOT["motor en memoria"]
    D[("administracion.json<br/>bitacora de cambios")] -->|"se reaplica al arrancar"| MOT
    MOT --> INV["modulo de investigacion"]
    MOT --> ADM["modulo administrativo"]
```

Y como cada baja guarda el texto de los hechos que se llevó, la bitácora se
puede recorrer al revés: eso es **restaurar valores de fábrica**, y es lo que
permite demostrar el CRUD sobre los casos reales sin arruinarlos.

---

## 3. Diagrama de flujo de la investigación

Recorrido de las acciones del usuario dentro del módulo de investigación y de
los datos que las acompañan.

```mermaid
flowchart TD
    INICIO(["Inicio"]) --> LISTA["Listado de casos<br/>filtro por dificultad y estado"]
    LISTA -->|"elige un caso"| SEL{"El caso<br/>tiene hechos?"}
    LISTA -->|"caso al azar"| SEL

    SEL -->|"no · pendiente"| AVISO["Aviso: el caso<br/>aun no esta cargado"]
    AVISO --> LISTA

    SEL -->|"si"| DESC["Descripcion inicial<br/>del incidente"]
    DESC --> ACC{"Accion de<br/>investigacion"}

    ACC -->|"consultar"| A1["Sospechosos · lugares<br/>evidencias · relaciones"]
    ACC -->|"interrogar"| A2["Declaraciones de<br/>sospechosos y testigos"]
    ACC -->|"analizar"| A3["Motivos · oportunidades<br/>coartadas · linea temporal"]
    ACC -->|"deducir"| A4["Contradicciones<br/>nivel de sospecha"]
    ACC -->|"pedir ayuda"| A5["Pista del sistema"]

    A1 --> BIT["Registrar la accion<br/>en la bitacora"]
    A2 --> BIT
    A3 --> BIT
    A4 --> BIT
    A5 --> BIT

    BIT --> LISTO{"Suficiente<br/>informacion?"}
    LISTO -->|"no"| ACC
    LISTO -->|"si"| ACU["Acusacion final<br/>contra un sospechoso"]

    ACU --> EVAL["Prolog compara con<br/>responsable/1"]
    EVAL --> VER{"Veredicto"}
    VER -->|"correcta"| OK["Acusacion correcta"]
    VER -->|"incorrecta"| NO["Acusacion incorrecta"]

    OK --> EXP["Explicacion logica:<br/>reglas activadas y su detalle"]
    NO --> EXP
    EXP --> FIN(["Informe final del caso"])
```

> Todo el recorrido está implementado. Las acciones de investigación son
> enlaces y formularios explícitos (`?analisis=`, `POST .../examinar`,
> `POST .../interrogar`, `POST .../pista`): cada una queda en la bitácora, así
> que ninguna se dispara al abrir la página. La descripción inicial del
> incidente es lo único que se ve antes de abrir la investigación.

---

## 4. Modelo de la base de conocimiento

### 4.1 Cadena de inferencia

De los hechos que aporta cada caso hasta la conclusión. Cada flecha es una
dependencia real entre predicados de `reglas_base.pl`.

```mermaid
graph TD
    subgraph HECHOS["HECHOS · los aporta cada casoN.pl"]
        h1["lugar_conectado<br/>tiene_llave · autorizado_en"]
        h2["registro_acceso<br/>visto_en · hora_del_incidente"]
        h3["motivo"]
        h4["posee_medio<br/>medio_requerido"]
        h5["coartada"]
        h6["declaracion"]
        h7["evidencia<br/>evidencia_incrimina"]
        h8["relacion"]
    end

    subgraph INTERMEDIAS["REGLAS INTERMEDIAS"]
        r1["conectado → ruta → alcanzable<br/><i>recursivo</i>"]
        r2["acceso_al_lugar"]
        r3["presente_en_ventana<br/>tuvo_oportunidad"]
        r4["tiene_motivo"]
        r5["tiene_medios"]
        r6["respaldo_confiable<br/>coartada_contradicha"]
        r7["coartada_valida<br/>coartada_invalida"]
        r8["declaracion_contradice_declaracion<br/>declaracion_contradice_evidencia"]
        r9["informacion_falsa"]
        r10["evidencia_contra<br/>evidencia_directa_contra<br/>evidencias_contra"]
    end

    subgraph PUNTAJE["ACUMULACION DE SOSPECHA"]
        p1["indicio/2<br/>8 tipos de indicio"]
        p2["peso/2 → suma_pesos<br/><i>recursivo</i>"]
        p3["puntaje_sospecha"]
        p4["nivel_sospecha<br/>clasificar_sospecha"]
        p5["ranking_sospecha"]
    end

    subgraph CONCLUSION["CONCLUSION"]
        c1["sospechoso_principal"]
        c2["responsable/1"]
        c3["posible_complice"]
        c4["explicacion/2<br/>veredicto/2"]
    end

    h1 --> r1 --> r2
    h1 --> r2
    h2 --> r3
    h3 --> r4
    h4 --> r5
    h5 --> r6 --> r7
    h2 --> r6
    h6 --> r8 --> r9
    h7 --> r8
    h7 --> r10

    r2 --> p1
    r3 --> p1
    r4 --> p1
    r5 --> p1
    r7 --> p1
    r9 --> p1
    r10 --> p1

    p1 --> p2 --> p3 --> p4 --> p5
    p3 --> c1 --> c2
    c1 --> c3
    h8 --> c3
    r9 --> c3
    c2 --> c4
    p1 --> c4
```

`responsable/1` no se conforma con el puntaje: vuelve a exigir directamente
oportunidad, motivo, medios, ausencia de coartada válida y dos evidencias en
contra. Esas condiciones se detallan en el apartado 4.3.

### 4.2 Ponderación de los indicios

`puntaje_sospecha/2` suma el peso de cada indicio detectado. La evidencia física
y la mentira comprobada pesan más que el acceso, que casi cualquiera tiene.

| Indicio | Peso | Se activa cuando |
| --- | --- | --- |
| `acceso` | 1 | Pudo entrar a la escena |
| `oportunidad` | 2 | Estuvo en la ventana de tiempo |
| `motivo` | 2 | Tiene razones |
| `medios` | 2 | Contaba con lo que el incidente exigió |
| `multiples_evidencias` | 2 | Hay 2 o más evidencias en su contra |
| `coartada_invalida` | 3 | Su coartada no se sostiene |
| `informacion_falsa` | 3 | Mintió y se puede probar |
| `evidencia_directa` | 3 | Hay huella, ADN o video en su contra |

Máximo posible: **18 puntos**. Clasificación por rangos:

| Puntaje | Nivel |
| --- | --- |
| ≥ 12 | `muy_alto` |
| ≥ 8 | `alto` |
| ≥ 4 | `medio` |
| ≥ 1 | `bajo` |
| 0 | `nulo` |

### 4.3 Condiciones de `responsable/1`

La conclusión del caso es deliberadamente exigente. **Nunca concluye con una
sola evidencia**, que es justo lo que pide el valor formativo del enunciado
("evitar acusaciones basadas en una sola evidencia").

```mermaid
flowchart TD
    P["Persona"] --> C1{"es el<br/>sospechoso<br/>principal?"}
    C1 -->|no| RECHAZA["No es responsable"]
    C1 -->|si| C2{"hay empate<br/>con otro?"}
    C2 -->|si| RECHAZA
    C2 -->|no| C3{"tuvo<br/>oportunidad?"}
    C3 -->|no| RECHAZA
    C3 -->|si| C4{"tiene<br/>motivo?"}
    C4 -->|no| RECHAZA
    C4 -->|si| C5{"tiene<br/>medios?"}
    C5 -->|no| RECHAZA
    C5 -->|si| C6{"tiene coartada<br/>valida?"}
    C6 -->|si| RECHAZA
    C6 -->|no| C7{"2 o mas<br/>evidencias<br/>en contra?"}
    C7 -->|no| RECHAZA
    C7 -->|si| ACEPTA["Responsable del caso"]
```

Un corte final deja el predicado `semidet`: el caso tiene un solo responsable y
no hace falta buscar otras derivaciones del mismo hecho.

### 4.4 Aislamiento entre casos

Cada caso es un módulo con lista de exportación vacía que incluye las reglas
textualmente:

```mermaid
graph TD
    RB["reglas_base.pl<br/>solo reglas, ningun hecho"]

    subgraph M1["modulo caso1"]
        R1["copia de las reglas"] --- F1["hechos del caso 1"]
    end
    subgraph M2["modulo caso2"]
        R2["copia de las reglas"] --- F2["hechos del caso 2"]
    end
    subgraph M3["modulo caso3"]
        R3["copia de las reglas"] --- F3["hechos del caso 3"]
    end

    RB -->|"include/1"| R1
    RB -->|"include/1"| R2
    RB -->|"include/1"| R3

    LD["logic_detective.pl<br/>caso_modulo/1 · consulta/2 · api_*"] --> M1
    LD --> M2
    LD --> M3
```

Por eso `caso1` y `caso2` pueden tener sospechosos con el mismo nombre sin
interferir, y por eso dos integrantes pueden trabajar en paralelo sin conflictos.

---

## 5. Decisiones de diseño

| Decisión | Por qué | Qué pasaría si se cambia |
| --- | --- | --- |
| **`include/1` y no `use_module/1`** | Las reglas tienen que resolverse contra los hechos *de ese módulo* | Con `use_module` las reglas buscarían hechos en el módulo de origen, que no tiene ninguno |
| **Un módulo por caso, exportación vacía** | Aislamiento total entre casos | Colisión de nombres: el `bruno` del caso 1 se mezclaría con el del caso 2 |
| **Fachada `api_*` plana** | PySwip 0.3.x no traduce términos anidados: una lista de átomos llega como `Atom('764549')` | Los datos llegarían corruptos a la interfaz |
| **Un solo worker en el backend** | SWI-Prolog se carga en el proceso y no se comparte entre procesos | Cada worker tendría su propia máquina Prolog, o fallaría al inicializar |
| **Candado en `MotorProlog`** | SWI-Prolog no es seguro para llamadas concurrentes desde varios hilos | Corrupción de memoria bajo carga |
| **Validación con `atomo()`** | Las metas se arman concatenando texto | Inyección de código Prolog, equivalente a un SQL injection |
| **Compilar Prolog en el `docker build`** | Un error de sintaxis falla en el build, con archivo y línea | Fallaría con el contenedor ya corriendo, y más difícil de diagnosticar |
| **El backend arranca aunque Prolog falle** | Permite diagnosticar el contenedor por `/health` | El contenedor moriría al arrancar sin decir por qué |
| **Administración escribe con `assertz`/`retractall`, no editando los `.pl`** | Los `.pl` mezclan hechos y reglas; reescribirlos desde la interfaz haría que un error de formato dejara el proyecto sin arrancar | Cada alta tendría que regenerar código fuente y recargar el motor |
| **Los cambios se guardan como bitácora, no como estado final** | Permite reaplicarlos al arrancar y, sobre todo, deshacerlos en orden inverso | Sin bitácora no habría «restaurar valores de fábrica», y una eliminación sería irreversible |
| **`terminos.py` es la única forma de construir un término** | Administración interpola registros enteros con texto libre, no solo identificadores | Una comilla en una descripción rompería la cláusula; un valor malicioso sería inyección de Prolog |
| **Las ocho entidades de la interfaz son datos, no ocho plantillas** | Una sola plantilla recorre `ENTIDADES` | Ochocientas líneas de plantilla casi idéntica, que se desincronizarían entre sí |

---

## 6. Despliegue

```mermaid
graph TB
    subgraph INTERNET["Internet"]
        NAV["Navegador<br/>del usuario"]
    end

    subgraph NUBE["Maquina virtual · AWS EC2 o GCP Compute Engine"]
        FW["Firewall<br/>8080/tcp abierto"]

        subgraph COMPOSE["Docker Compose"]
            CF["logic-detective-frontend<br/>gunicorn · 8080<br/>healthcheck /salud"]
            CB["logic-detective-backend<br/>uvicorn 1 worker · 8000<br/>healthcheck /health<br/>swi-prolog-nox incluido"]
        end
    end

    subgraph GH["GitHub"]
        REPO["Repositorio"]
        CI["GitHub Actions<br/>lint · prolog · tests · docker"]
    end

    NAV -->|"HTTP :8080"| FW --> CF
    CF -->|"red interna de Compose<br/>http://backend:8000"| CB
    REPO --> CI
    CI -.->|"CD · pendiente"| COMPOSE
```

| Aspecto | Valor |
| --- | --- |
| Puerto público | **8080** (interfaz) |
| Puerto interno | 8000 (API) — solo se expone si se quiere publicar `/docs` |
| Resolución entre contenedores | Por nombre de servicio: `http://backend:8000` |
| Orden de arranque | La interfaz espera a que el backend esté **sano**, no solo arrancado |
| Variables a definir | `SECRET_KEY` con un valor propio; `TZ=America/Guatemala` |
| Reinicio | `restart: unless-stopped` en ambos servicios |

El frontend llega al backend por la red interna de Compose, así que **no es
necesario exponer el 8000** para que la aplicación funcione.

> **Estado:** el sistema está contenedorizado, probado y con CI funcionando.
> Falta ejecutar el despliegue en la VM y agregar el paso de CD al pipeline.
> Al completarlo hay que anotar aquí la URL de la instancia.

---

## 7. Pruebas automatizadas

```mermaid
graph LR
    subgraph CI["GitHub Actions · 4 trabajos en paralelo"]
        J1["Lint<br/>ruff check + format"]
        J2["Base de conocimiento<br/>compila logic_detective.pl<br/>y reglas_base.pl"]
        J3["Pruebas<br/>pytest sobre Prolog real"]
        J4["Contenedores<br/>build + up + healthchecks"]
    end

    subgraph SUITE["Suite de pruebas"]
        T1["test_api.py<br/>FastAPI → PySwip → Prolog<br/>incluye inyeccion"]
        T2["test_prolog_integracion.py<br/>reglas + los 10 casos<br/>del enunciado"]
        T3["test_frontend.py<br/>filtros y rutas<br/>backend simulado"]
        T4["test_investigaciones.py<br/>descubrimiento progresivo<br/>puntaje y bitacora"]
        T5["test_admin.py<br/>CRUD, validaciones,<br/>persistencia y su efecto<br/>sobre la deduccion"]
    end

    J3 --> T1
    J3 --> T2
    J3 --> T3
    J3 --> T4
    J3 --> T5
```

`reglas_base.pl` se compila **por separado** a propósito: un error de sintaxis
ahí rompe los tres casos a la vez, porque los tres la incluyen.
