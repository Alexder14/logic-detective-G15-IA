# Manual técnico

**Proyecto 1 — Logic Detective** · Inteligencia Artificial 1 · Sección A · Grupo 15
Facultad de Ingeniería, USAC · Segundo semestre 2026

Documento dirigido a quien tenga que instalar, modificar o desplegar el sistema.
El uso de la aplicación está en [`MANUAL_USUARIO.md`](MANUAL_USUARIO.md) y los
diagramas en [`ARQUITECTURA.md`](ARQUITECTURA.md).

---

## 1. Requisitos

| Componente | Versión | Para qué |
| --- | --- | --- |
| Python | 3.12 (mínimo 3.11) | Backend, interfaz y pruebas |
| SWI-Prolog | 9.x (`swi-prolog-nox`) | Motor de inferencia |
| Docker + Docker Compose | 24.x o superior | Contenedores y despliegue |
| Git | 2.x | Repositorio |

**SWI-Prolog es obligatorio incluso para desarrollo local.** PySwip no incluye
Prolog: carga la biblioteca `libswipl` del sistema por FFI. Sin ella el backend
arranca pero `/health` responde 503.

Dependencias de Python, fijadas por versión exacta:

| Archivo | Paquetes |
| --- | --- |
| `backend/requirements.txt` | `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`, `pyswip==0.3.3` |
| `frontend/requirements.txt` | `flask==3.1.0`, `requests==2.32.3`, `gunicorn==23.0.0` |
| `tests/requirements.txt` | los dos anteriores + `pytest==8.3.4`, `httpx==0.28.1`, `ruff==0.8.6` |

---

## 2. Instalación

### 2.1 Con Docker (recomendado)

Es la forma en que se evalúa y se despliega. Levanta los dos servicios y espera
a que el backend reporte que Prolog respondió.

```bash
git clone <url-del-repositorio>
cd logic-detective-G15-IA
docker compose up --build
```

| Servicio | URL | Puerto |
| --- | --- | --- |
| Interfaz web | http://localhost:8080 | 8080 |
| API | http://localhost:8000 | 8000 |
| Documentación interactiva de la API | http://localhost:8000/docs | 8000 |

Apagar: `docker compose down`

### 2.2 Instalación local (desarrollo)

```bash
# 1. SWI-Prolog
sudo apt install swi-prolog-nox        # Debian/Ubuntu
swipl --version                        # verificar

# 2. Entorno virtual e instalación
python3 -m venv .venv
source .venv/bin/activate
pip install -r tests/requirements.txt  # arrastra backend y frontend

# 3. Terminal 1 — backend
uvicorn app.main:app --reload --app-dir backend --port 8000

# 4. Terminal 2 — interfaz
BACKEND_URL=http://localhost:8000 python frontend/app.py
```

### 2.3 Verificación de la instalación

```bash
curl -s localhost:8000/health
# {"estado":"ok","prolog":"conectado","version_motor":"1.0.0-esqueleto", ...}

curl -s localhost:8080/salud
# {"estado":"ok","backend":"http://localhost:8000"}
```

Si `/health` devuelve 503, el JSON trae el error concreto de PySwip. El backend
se levanta a propósito aunque Prolog falle, para poder diagnosticar el
contenedor en lugar de que muera al arrancar.

### 2.4 Variables de entorno

| Variable | Servicio | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `BACKEND_URL` | interfaz | `http://localhost:8000` | Dentro de Compose es `http://backend:8000` |
| `SECRET_KEY` | interfaz | `logic-detective-dev` | **Cambiar en el despliegue.** Firma la sesión de Flask |
| `PORT` | interfaz | `8080` | |
| `TZ` | ambos | `America/Guatemala` | Para que los logs cuadren con la hora local |

---

## 3. Arquitectura

```
┌──────────────┐      HTTP       ┌──────────────┐     PySwip      ┌──────────────┐
│   frontend   │ ──────────────► │   backend    │ ──────────────► │    Prolog    │
│ Flask+Jinja2 │ ◄────────────── │   FastAPI    │ ◄────────────── │  SWI-Prolog  │
│    :8080     │      JSON       │    :8000     │   soluciones    │ reglas_base  │
└──────────────┘                 └──────────────┘                 └──────────────┘
```

Regla de diseño que atraviesa todo el proyecto: **toda deducción ocurre en
Prolog.** Python orquesta, traduce y presenta. Si aparece un `if` en Python que
decide quién es culpable, esa lógica está en el lugar equivocado.

Recorrido de una consulta, por ejemplo `GET /api/casos/caso_demo/conclusion`:

1. El navegador pide `/investigacion/caso_demo` a Flask.
2. Flask llama por HTTP a FastAPI (`frontend/app.py`, función `api()`).
3. FastAPI valida el identificador y arma la meta Prolog como texto.
4. `MotorProlog.filas()` la ejecuta con PySwip, bajo un candado.
5. SWI-Prolog resuelve por unificación y backtracking sobre `reglas_base.pl`
   aplicado a los hechos del módulo del caso.
6. Cada solución vuelve como un diccionario de Python y se serializa a JSON.
7. Jinja2 dibuja la plantilla.

### 3.1 Estructura de carpetas

```
logic-detective-G15-IA/
├── prolog/                     Motor de inferencia
│   ├── reglas_base.pl          Reglas compartidas por los 3 casos (sin hechos)
│   ├── logic_detective.pl      Cargador + fachada api_* que consume el backend
│   ├── caso_demo.pl            Caso mínimo de referencia
│   └── caso1.pl caso2.pl caso3.pl
├── backend/
│   ├── app/main.py             Endpoints FastAPI
│   ├── app/prolog_engine.py    ÚNICO punto de contacto con PySwip
│   └── Dockerfile
├── frontend/
│   ├── app.py                  Servidor Flask
│   ├── templates/              base, inicio, investigacion, caso, informe, admin
│   ├── static/estilos.css
│   └── Dockerfile
├── tests/
├── docs/
├── .github/workflows/ci.yml
└── docker-compose.yml
```

---

## 4. Referencia de la API

Base: `http://localhost:8000`. Todas las respuestas son JSON.
La documentación interactiva y navegable se genera sola en `/docs` (OpenAPI).

Cada endpoint se traduce a uno o más predicados `api_*` de
`prolog/logic_detective.pl`. Esa correspondencia es el contrato entre Python y
Prolog:

| Método y ruta | Predicado Prolog | Devuelve |
| --- | --- | --- |
| `GET /health` | `version_motor/1` | Estado del motor |
| `GET /api/casos` | `api_caso/10`, `api_caso_de_ejemplo/1` | Lista de casos con estado y conteos. Acepta `?dificultad=` y `?estado=` |
| `GET /api/casos/{id}` | `api_caso/10`, `api_caso_de_ejemplo/1` | Descripción inicial del incidente |
| `GET /api/casos/{id}/sospechosos` | `api_sospechoso/4` + `api_indicio/3` | Personas con nivel de sospecha, puntaje e indicios |
| `GET /api/casos/{id}/evidencias` | `api_evidencia/7` + `api_evidencia_incrimina/3` | Evidencias y a quién incriminan |
| `GET /api/casos/{id}/lugares` | `api_lugar/4` | Lugares y cuál es la escena |
| `GET /api/casos/{id}/declaraciones` | `api_declaracion/4` | Testimonios |
| `GET /api/casos/{id}/coartadas` | `api_coartada/4` | Coartadas y si son válidas |
| `GET /api/casos/{id}/relaciones` | `api_relacion/6` | Vínculos entre las personas, marcando los conflictivos y a la víctima |
| `GET /api/casos/{id}/motivos` | `api_motivo/3` | Motivos por persona |
| `GET /api/casos/{id}/oportunidades` | `api_oportunidad/3` | Quién pudo estar en la escena sin coartada que lo descarte |
| `GET /api/casos/{id}/contradicciones` | `api_contradiccion/4` | Inconsistencias detectadas |
| `GET /api/casos/{id}/linea-temporal` | `api_evento/4` | Eventos ordenados por hora |
| `GET /api/casos/{id}/pistas` | `api_pista/2` | Pistas del sistema |
| `GET /api/casos/{id}/conclusion` | `api_conclusion/3`, `api_veredicto/5`, `api_explicacion/4` | Responsable, cómplices y **reglas activadas** |
| `POST /api/casos/{id}/acusacion` | `api_acusacion/4` | Veredicto de la acusación |
| `GET /api/admin/estado` | `api_caso/10`, `estado_caso/3`, `api_reglas_propias/2` | Avance de los casos contra los cinco mínimos, reglas de inferencia incluidas |

Los endpoints del descubrimiento progresivo y la bitácora. Una **investigación**
es una partida sobre un caso: vive en la memoria del backend
(`backend/app/investigaciones.py`), no en Prolog, porque es estado del usuario y
no conocimiento del caso.

| Método y ruta | Predicado Prolog | Devuelve |
| --- | --- | --- |
| `POST /api/casos/{id}/investigaciones` | — | Abre una investigación: id y puntaje inicial (100) |
| `GET …/investigaciones/{inv}/bitacora` | — | Puntaje y acciones registradas, en orden |
| `GET …/investigaciones/{inv}/informe` | `api_conclusion/3`, `api_veredicto/5`, `api_explicacion/4` | Informe final: avance, bitácora y conclusión |
| `POST …/evidencias/{id}/examinar` | `api_evidencia/7` + `api_evidencia_incrimina/3` | La evidencia, y la marca como examinada |
| `POST …/declaraciones/{id}/interrogar` | `api_declaracion/4` | La declaración, y la marca como interrogada |
| `POST …/pistas/siguiente` | `api_pista/2` | La próxima pista sin usar. Descuenta 5 puntos |

Los endpoints de solo lectura aceptan además `?investigacion_id=`. Con él,
`evidencias` y `declaraciones` devuelven **solo lo ya descubierto**, y los demás
registran la consulta en la bitácora. Sin él devuelven todo y no registran nada,
que es el modo de referencia o administrativo.

### 4.1 Ejemplos

```bash
# Listado de casos
curl -s localhost:8000/api/casos | python -m json.tool

# La conclusión, con la justificación lógica que exige la rúbrica
curl -s localhost:8000/api/casos/caso_demo/conclusion | python -m json.tool

# Acusación
curl -s -X POST localhost:8000/api/casos/caso_demo/acusacion \
     -H 'Content-Type: application/json' \
     -d '{"sospechoso":"bruno"}'
# {"acusado":"bruno","veredicto":"correcta","responsable":"bruno"}
```

### 4.2 Códigos de estado

| Código | Cuándo |
| --- | --- |
| `200` | Todo bien. Una lista vacía **no** es error: significa que el caso todavía no tiene hechos |
| `400` | El identificador recibido no es un átomo de Prolog válido |
| `404` | El caso o la persona no existen en la base de conocimiento |
| `500` | La consulta a Prolog lanzó una excepción |
| `503` | El motor no está disponible (falta SWI-Prolog o PySwip) |

### 4.3 Validación de entradas

Las metas de Prolog se arman concatenando texto, así que **todo lo que venga del
cliente y termine dentro de una meta pasa por `atomo()`** (`backend/app/main.py`),
que exige la forma `^[a-z][a-zA-Z0-9_]{0,63}$`.

Sin esa validación un parámetro como `caso1), halt, foo(` se ejecutaría como
código Prolog: es una inyección equivalente a un SQL injection. Hay pruebas
específicas para esto en `tests/test_api.py`.

### 4.4 Rutas de la interfaz

| Ruta | Método | Descripción |
| --- | --- | --- |
| `/` | GET | Inicio: nombre, propósito, casos y accesos a los dos módulos |
| `/investigacion` | GET | Listado de casos. Acepta `?dificultad=` y `?estado=`, que reenvía al backend |
| `/investigacion/aleatorio` | GET | Sortea un caso con hechos cargados y redirige |
| `/investigacion/<caso>` | GET | Expediente del caso. Con investigación abierta, el panel de trabajo. Acepta `?analisis=` |
| `/investigacion/<caso>/abrir` | POST | Abre una investigación nueva (también sirve para reiniciar) |
| `/investigacion/<caso>/evidencias/<id>/examinar` | POST | Examina una evidencia |
| `/investigacion/<caso>/declaraciones/<id>/interrogar` | POST | Interroga a quien dio una declaración |
| `/investigacion/<caso>/pista` | POST | Pide la próxima pista |
| `/investigacion/<caso>/acusacion` | POST | Acusación final |
| `/investigacion/<caso>/informe` | GET | Informe final de la investigación |
| `/admin` | GET | Avance de los casos y las investigaciones de la sesión |
| `/salud` | GET | Healthcheck del contenedor |

### 4.5 Descubrimiento progresivo en la interfaz

Tres decisiones del frontend que no se leen solas en el código:

1. **La cookie guarda solo el id.** `session["investigaciones"]` es
   `{caso_id: investigacion_id}`; todo el progreso vive en el backend. Como las
   investigaciones son estado en memoria, un reinicio del backend deja la cookie
   apuntando a la nada: la vista del caso lo detecta cuando la bitácora responde
   404, olvida el id y ofrece abrir una nueva.

2. **Dos llamadas por lista.** Para dibujar el botón «Examinar» hacen falta los
   identificadores de las evidencias, y esos solo salen de la llamada sin
   `investigacion_id`. La interfaz junta las dos listas en `descubrimiento()` y
   de lo que todavía no se descubrió deja pasar únicamente el id —el autor, en
   las declaraciones—, así el dato que el detective no descubrió nunca llega al
   HTML. Hay pruebas de esa propiedad en `tests/test_frontend.py`.

3. **Los análisis son enlaces, no carga automática.** Consultar sospechosos,
   lugares, relaciones, coartadas, motivos, oportunidades, contradicciones o la
   línea temporal queda registrado en la bitácora, así que se piden de a uno con
   `?analisis=`. Si la vista los
   cargara todos al abrir el caso, la bitácora diría qué renderizó Flask en vez
   de qué hizo el detective.

---

## 5. Referencia de la base de conocimiento

### 5.1 Organización

`reglas_base.pl` contiene **las reglas y ningún hecho**. Cada caso es un módulo
independiente que la incluye textualmente:

```prolog
:- module(caso1, []).
:- include('reglas_base.pl').
% ... hechos del caso 1 ...
```

Se usa `include/1` y no `use_module/1` a propósito: las reglas tienen que
resolverse contra los hechos *de ese módulo*. Como la lista de exportación es
vacía, `caso1` y `caso2` pueden tener sospechosos con el mismo nombre sin
interferir entre sí.

> **Cómo se cuentan las reglas propias de un caso.** Como el `include` es
> textual, las reglas compartidas aparecen como definidas en el módulo del caso
> y no alcanza con mirar el módulo. `reglas_propias/2` las separa por el archivo
> de origen de cada cláusula (`clause_property/2`) y cuenta predicados, no
> cláusulas: un predicado con tres cláusulas es una regla con tres casos. Es el
> criterio más conservador, así que si el número llega al mínimo, llega de
> sobra. Es el quinto mínimo del enunciado y `estado_caso/3` ahora lo exige para
> declarar un caso `completo`.

### 5.2 Esquema de hechos

Es el **único punto de acoplamiento** del proyecto. Está documentado en el
encabezado de `reglas_base.pl` y quien escriba un caso debe respetarlo:

| Categoría | Predicados |
| --- | --- |
| Ficha | `caso/4` — Id, Título, Descripción, Dificultad (`facil\|media\|dificil`) |
| Personas | `sospechoso/1`, `testigo/1`, `victima/1`, `relacion/3` |
| Lugares | `lugar/2`, `escena_del_incidente/1`, `lugar_conectado/2`, `hora_del_incidente/1` |
| Acceso | `tiene_llave/2`, `autorizado_en/2`, `registro_acceso/3`, `visto_en/3` |
| Motivo | `motivo/2` — `deuda\|herencia\|venganza\|celos\|despido\|encubrimiento\|dinero` |
| Medios | `medio_requerido/1`, `posee_medio/2` |
| Evidencia | `evidencia/5`, `evidencia_incrimina/2` |
| Testimonio | `declaracion/3` |
| Coartada | `coartada/4` — Persona, Lugar, Hora, Respaldo |

El contenido de `declaracion/3` debe ser uno de estos términos, porque las
reglas detectan contradicciones por unificación sobre ellos:

```
estuvo_en(Persona, Lugar, Hora)      no_estuvo_en(Persona, Lugar, Hora)
vio_a(Persona, Lugar, Hora)          conoce_a(P1, P2)
no_conoce_a(P1, P2)                  posee(Persona, Medio)
```

Todos los predicados de hechos se declaran `dynamic`, de modo que un caso a
medio escribir falla la consulta en vez de lanzar `existence_error`.

### 5.3 Reglas derivadas principales

Definidas en `reglas_base.pl`, disponibles para los tres casos:

| Predicado | Qué infiere |
| --- | --- |
| `acceso_al_lugar/2` | Quién pudo entrar al lugar |
| `tuvo_oportunidad/2` | Quién estuvo en la ventana de tiempo del incidente |
| `tiene_motivo/2` | Quién tenía razones |
| `tiene_medios/2` | Quién contaba con lo que el incidente exigió |
| `coartada_valida/2`, `coartada_invalida/2` | Validación de coartadas y su razón |
| `declaracion_contradice_declaracion/2` | Testimonios incompatibles entre sí |
| `declaracion_contradice_evidencia/2` | Testimonio contra evidencia física |
| `informacion_falsa/1` | Quién mintió |
| `indicio/2`, `peso/2`, `puntaje_sospecha/2` | Acumulación ponderada de indicios |
| `nivel_sospecha/2` | `muy_alto\|alto\|medio\|bajo\|nulo` |
| `ranking_sospecha/1` | Orden de mayor a menor sospecha |
| `sospechoso_principal/1` | El de mayor puntaje |
| `responsable/1` | **Conclusión del caso. Debe dar una sola respuesta** |
| `posible_complice/2` | Cómplices |
| `explicacion/2` | Reglas activadas para justificar la conclusión |
| `veredicto/2`, `linea_temporal/1`, `pista/1`, `resumen_caso/1` | Salidas para la interfaz |

`ruta/3` y `alcanzable/2` son recursivos sobre `lugar_conectado/2`; junto con
`findall/3`, `\+` y los cortes cubren los elementos de Prolog que la rúbrica
exige demostrar (listas, recursividad, unificación, negación y cortes).

### 5.4 La fachada `api_*`

`logic_detective.pl` expone una capa plana sobre las reglas. Cada `api_*/N`
devuelve **una fila por solución, con argumentos atómicos: nunca listas ni
términos compuestos**.

La razón es PySwip 0.3.x, que no traduce bien los términos anidados — una lista
de átomos dentro de un término llega a Python como `Atom('764549')`. Lo que sea
un término compuesto del dominio se entrega ya convertido a cadena con `texto/2`.

> **Si te falta un dato en Python, agregá un `api_*` plano en Prolog.** No
> desarmes términos de Prolog dentro de Python ni metas decisiones en Python.

Consultas directas desde la línea de comandos, sin levantar nada:

```bash
swipl prolog/logic_detective.pl
?- consulta(caso_demo, responsable(P)).
?- estado_caso(caso1, Estado, Resumen).
?- caso_demo:ranking_sospecha(R).
```

---

## 6. Cómo agregar un caso nuevo

1. **Crear el archivo** `prolog/caso4.pl` partiendo de `prolog/caso_demo.pl`,
   que sirve de ejemplo de formato:

   ```prolog
   :- module(caso4, []).
   :- include('reglas_base.pl').

   caso(caso4, 'Título', 'Descripción del incidente.', media).
   % ... hechos, respetando el esquema de la sección 5.2 ...
   ```

2. **Registrarlo** en `prolog/logic_detective.pl`: agregar el `ensure_loaded` y
   una línea en `caso_modulo/1`.

3. **Probarlo aisladamente** antes de integrarlo:

   ```bash
   swipl prolog/caso4.pl
   ?- caso4:resumen_caso(R).       % ¿cumple los conteos mínimos?
   ?- caso4:ranking_sospecha(R).   % ¿el orden es el esperado?
   ?- caso4:responsable(P).        % debe dar UNA sola respuesta
   ```

4. **Agregar pruebas** en `tests/test_prolog_integracion.py`.

No hace falta tocar Python ni la interfaz: el caso aparece solo en el listado y
en el módulo administrativo.

**Mínimos por caso que exige el enunciado:** 4 sospechosos, 10 evidencias,
5 lugares, 5 declaraciones y 10 reglas de inferencia propias. Mientras no se
cumplan, el caso se muestra como `incompleto`.

Ver el avance de todos los casos en cualquier momento:

```bash
swipl -q -g "consult('prolog/logic_detective.pl'), \
  forall(api_caso(M,_,_,_,_,E,NS,NE,NL,ND), \
    format('~w: ~w (~w/4 sosp, ~w/10 evid, ~w/5 lug, ~w/5 decl)~n', \
      [M,E,NS,NE,NL,ND])), halt"
```

---

## 7. Pruebas

```bash
pip install -r tests/requirements.txt
pytest -v                              # suite completa
pytest tests/test_frontend.py -v       # solo la interfaz
ruff check . && ruff format --check .  # lint y formato
```

| Archivo | Qué cubre | Necesita Prolog |
| --- | --- | --- |
| `tests/test_api.py` | Endpoints de principio a fin: FastAPI → PySwip → Prolog. Incluye intentos de inyección | Sí |
| `tests/test_prolog_integracion.py` | Reglas de inferencia y los 10 casos de prueba del enunciado | Sí |
| `tests/test_frontend.py` | Capa de presentación: filtros, rutas y plantillas, con el backend simulado | No |

`tests/conftest.py` inicializa **una sola instancia** de SWI-Prolog por sesión
(fixture `motor`, alcance `session`): PySwip arranca una única máquina Prolog
dentro del proceso y reinicializarla en cada prueba es lento y frágil.

La interfaz se carga con `importlib` bajo el nombre `interfaz_web`, porque
`frontend/app.py` y el paquete `backend/app/` competirían por el nombre `app` en
`sys.modules`.

Los 10 casos de prueba del enunciado están como plantilla con `skip`. Cada
responsable de caso activa los suyos quitando el `skip` correspondiente. La meta
de la rúbrica es 80 % de aciertos.

---

## 8. Contenedores

Ambas imágenes parten de `python:3.12-slim-bookworm`, corren como usuario sin
privilegios (`detective`, uid 1000) y traen `HEALTHCHECK`.

**El contexto de build de los dos servicios es la raíz del repositorio**, no
`backend/` ni `frontend/`, porque la imagen del backend necesita copiar también
`prolog/`.

| | Backend | Frontend |
| --- | --- | --- |
| Puerto | 8000 | 8080 |
| Servidor | uvicorn, **1 worker** | gunicorn |
| Extra del sistema | `swi-prolog-nox`, `curl` | `curl` |
| Healthcheck | `/health` | `/salud` |

Dos decisiones que conviene no revertir sin entender por qué están:

- **Un solo worker en el backend.** SWI-Prolog se carga dentro del proceso y no
  se comparte entre procesos. Para escalar hay que levantar más réplicas del
  contenedor, no más workers. Además, `prolog_engine.py` protege las consultas
  con un candado porque SWI-Prolog no es seguro para llamadas concurrentes desde
  varios hilos.
- **El Dockerfile del backend compila la base de conocimiento durante el build.**
  Si un caso tiene un error de sintaxis, el build falla ahí, con archivo y línea,
  en lugar de fallar con el contenedor ya corriendo.

En Compose, la interfaz espera a que el backend esté **sano** (`condition:
service_healthy`), no solo arrancado: cargar la base de conocimiento toma un
momento.

---

## 9. Integración continua

`.github/workflows/ci.yml` corre en cada push a cualquier rama y en los pull
requests hacia `main` y `develop`. Cuatro trabajos independientes, en paralelo:

| Trabajo | Qué hace |
| --- | --- |
| **Lint de Python** | `ruff check` y `ruff format --check` |
| **Base de conocimiento** | Compila `logic_detective.pl` y `reglas_base.pl` por separado, y reporta el avance de cada caso |
| **Pruebas automatizadas** | Instala SWI-Prolog, verifica que PySwip lo encuentra y corre `pytest -v` |
| **Contenedores** | `docker compose build`, levanta el stack, verifica `/health`, la interfaz y `/admin`, y vuelca los logs si algo falla |

`reglas_base.pl` se compila por separado a propósito: un error de sintaxis ahí
rompe los tres casos a la vez, porque los tres la incluyen.

Si se empuja de nuevo a la misma rama, la corrida anterior se cancela
(`concurrency`).

---

## 10. Flujo de trabajo con Git

```
main        entregable estable. Solo recibe merges desde develop.
develop     integración. Aquí se juntan los aportes de todos.
feat/...    una rama por tarea, sale de develop y vuelve por pull request.
```

Mensajes de commit: prefijo, dos puntos y qué se hizo, en minúsculas.
Prefijos en uso: `feat`, `fix`, `test`, `docs`, `ci`, `refactor`, `chore`.

```
feat(prolog): agregar los 10 hechos de evidencia del caso 1
fix(prolog): corregir la coartada de la sospechosa 3
```

Cada integrante hace sus propios commits con su cuenta: son la evidencia que
respalda los porcentajes de participación del informe final.

Etiquetas de versión: `v0.1.0` marca el esqueleto; `v1.0.0`, la entrega final.

---

## 11. Despliegue

> **Estado: pendiente de ejecutar.** El sistema está contenedorizado y probado
> localmente; falta levantarlo en la máquina virtual. Al completarlo hay que
> anotar aquí la URL de la instancia.

El despliegue en GCP está automatizado en `deploy/`:

```bash
./deploy/desplegar-gcp.sh          # crea la VM, abre el puerto y levanta todo
./deploy/desplegar-gcp.sh --actualizar   # vuelve a subir el código y reconstruye
```

`deploy/arranque-vm.sh` es el *startup-script* de la instancia: instala Docker,
agrega 2 GB de swap —construir la imagen del backend con SWI-Prolog no cabe en
la memoria de la máquina— y fija la zona horaria. `deploy/desplegar-gcp.sh`
habilita la API de Compute Engine, crea la VM, abre el 8080, sube el código con
`git archive` y levanta los contenedores. También administra el ciclo de vida:
`--actualizar`, `--apagar`, `--encender`, `--eliminar` y `--estado`.

La configuración por omisión es la capa gratuita permanente de GCP: una
`e2-micro` en `us-central1` con 30 GB de disco `pd-standard`. Lo único
facturable es la IP externa, alrededor de USD 0.004 por hora.

Requisito previo, y lo único que no automatiza el script: el proyecto de GCP
necesita una **cuenta de facturación abierta**. Sin ella Google no permite
habilitar Compute Engine ni crear instancias, ni siquiera dentro de la capa
gratuita.

Equivalente manual, sobre una VM Ubuntu 22.04 en GCP o AWS:

```bash
# 1. En la VM: Docker
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER   # cerrar sesión y volver a entrar

# 2. Código
git clone <url-del-repositorio> && cd logic-detective-G15-IA

# 3. Clave de sesión propia (NO dejar la de desarrollo)
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env

# 4. Levantar
docker compose up -d --build
docker compose ps        # ambos servicios deben quedar "healthy"
```

Reglas de firewall necesarias: abrir **8080/tcp** (interfaz). El **8000** solo
si se quiere exponer la API y su documentación; no es necesario para que la
aplicación funcione, porque la interfaz llega al backend por la red interna de
Compose.

Actualizar la versión desplegada:

```bash
git pull && docker compose up -d --build
```

Diagnóstico:

```bash
docker compose logs -f backend     # o frontend
docker compose ps                  # estado de los healthchecks
curl -fsS localhost:8000/health
```

---

## 12. Resolución de problemas

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `/health` responde 503 | SWI-Prolog o PySwip no disponibles | `sudo apt install swi-prolog-nox` y reinstalar `pyswip`. El JSON de la respuesta trae el error exacto |
| La interfaz muestra "No se pudo contactar al backend" | El backend está caído o `BACKEND_URL` apunta mal | Verificar `curl localhost:8000/health` y el valor de `BACKEND_URL` |
| Un caso aparece como `pendiente` | `casoN.pl` todavía no tiene hechos | Es lo esperado hasta que su responsable lo llene |
| Un caso aparece como `incompleto` | Tiene hechos pero no llega a los mínimos | Ver el conteo en `/admin` o con el comando de la sección 6 |
| `caso_demo` aparece como `incompleto` | Es correcto: es la plantilla de referencia, no uno de los tres entregables | Nada. Sale marcado como `ejemplo` y la interfaz lo aclara |
| `?- casoN:responsable(P).` da más de una respuesta | El caso no discrimina lo suficiente entre sospechosos | Revisar motivos, medios y coartadas de los distractores |
| `existence_error` al consultar un caso | Se usó un predicado fuera del esquema | Revisar la sección 5.2 |
| `pytest` falla al importar `pyswip` | Se instaló PySwip antes que SWI-Prolog | Instalar Prolog primero y reinstalar `pyswip` |
| El build de Docker falla al compilar Prolog | Error de sintaxis en un `.pl` | El error trae archivo y línea. Verificar con `swipl prolog/casoN.pl` |
| Un valor de Prolog llega a Python como `Atom('764549')` | Se devolvió una lista o término anidado desde un `api_*` | Aplanar el predicado: una fila por solución, argumentos atómicos (sección 5.4) |

---

## 13. Referencias

- SWI-Prolog — https://www.swi-prolog.org/
- PySwip — https://pypi.org/project/pyswip/
- Docker y Docker Compose — https://docs.docker.com/
- GitHub Actions — https://docs.github.com/es/actions
- FastAPI — https://fastapi.tiangolo.com/
- Flask — https://flask.palletsprojects.com/
