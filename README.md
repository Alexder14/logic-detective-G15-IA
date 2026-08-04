# Logic Detective (grupo 15)

Sistema experto de investigación criminal. El motor de inferencia está escrito en
Prolog (SWI-Prolog) y se integra con una aplicación Python usando PySwip.

Proyecto 1 de Inteligencia Artificial 1, Facultad de Ingeniería, USAC,
segundo semestre 2026.

## Arquitectura

```
┌──────────────┐      HTTP       ┌──────────────┐     PySwip      ┌──────────────┐
│   frontend   │ ──────────────► │   backend    │ ──────────────► │    Prolog    │
│ Flask+Jinja2 │ ◄────────────── │   FastAPI    │ ◄────────────── │  SWI-Prolog  │
│  :8080       │      JSON       │   :8000      │   soluciones    │ reglas_base  │
└──────────────┘                 └──────────────┘                 └──────────────┘
```

Toda deducción va en Prolog. Python orquesta, traduce y presenta, nada más. Si
te ves escribiendo un `if` que decide quién es culpable, esa lógica va en un
predicado.

## Estructura de carpetas

```
logic-detective-G15-IA/
├── prolog/                     # Motor de inferencia (base de conocimiento)
│   ├── reglas_base.pl          # Reglas compartidas por los 3 casos    [LISTO]
│   ├── logic_detective.pl      # Cargador + fachada api_* del backend  [LISTO]
│   ├── caso_demo.pl            # Caso mínimo de referencia             [LISTO]
│   ├── caso1.pl                # Caso 1 — a llenar por el equipo
│   ├── caso2.pl                # Caso 2 — a llenar por el equipo
│   └── caso3.pl                # Caso 3 — a llenar por el equipo
├── backend/                    # API REST + integración PySwip
│   ├── app/
│   │   ├── main.py             # Aplicación FastAPI y endpoints
│   │   └── prolog_engine.py    # Único punto de contacto con PySwip
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Interfaz web (2 módulos)
│   ├── app.py                  # Servidor Flask
│   ├── templates/              # base, inicio, investigacion, caso, admin
│   ├── static/estilos.css
│   ├── requirements.txt
│   └── Dockerfile
├── tests/                      # Pruebas automatizadas
│   ├── conftest.py             # Motor de Prolog compartido por la sesión
│   ├── test_prolog_integracion.py  # + plantilla de los 10 casos de prueba
│   ├── test_api.py
│   └── requirements.txt
├── docs/                       # Documentación entregable
├── .github/workflows/ci.yml    # CI: lint, Prolog, pytest, contenedores
├── docker-compose.yml
├── .dockerignore
├── pytest.ini
└── README.md
```

`caso_demo.pl` no es uno de los tres casos entregables. Es un caso chico
(3 sospechosos, 5 evidencias) que sirve para probar la integración de punta a
punta mientras `caso1/2/3` están vacíos, y como ejemplo de formato. No cumple
los mínimos del enunciado.

## Contrato entre capas

El único punto de acoplamiento entre integrantes es el esquema de hechos que
consume `reglas_base.pl`, documentado en el encabezado de ese archivo. Mientras
lo respetes podés escribir tu caso sin tocar nada más del repositorio.

Cada caso es un módulo Prolog aparte (`:- module(caso1, [])`), así que dos
personas pueden usar los mismos nombres de sospechosos sin colisionar.

## Cómo levantar el proyecto

### Con Docker (recomendado)

```bash
docker-compose up --build
```

- Interfaz:            http://localhost:8080
- API:                 http://localhost:8000
- Documentación API:   http://localhost:8000/docs

### Local (desarrollo)

Requiere `swi-prolog` instalado en el sistema (`sudo apt install swi-prolog-nox`).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt -r frontend/requirements.txt -r tests/requirements.txt

# Terminal 1: backend
uvicorn app.main:app --reload --app-dir backend --port 8000

# Terminal 2: frontend
BACKEND_URL=http://localhost:8000 python frontend/app.py
```

### Pruebas

```bash
pip install -r tests/requirements.txt
pytest -v                 # requiere pyswip + swi-prolog
ruff check . && ruff format --check .
```

## Por dónde empieza cada quien

**Si te toca un caso (`prolog/casoN.pl`)**

1. Leé el encabezado de tu archivo: tiene la lista de mínimos y el esquema de
   hechos que debés respetar.
2. Mirá `prolog/caso_demo.pl` como ejemplo de formato.
3. Probá sin levantar nada más:
   ```bash
   swipl prolog/caso1.pl
   ?- caso1:resumen_caso(R).       % ¿ya cumplís los conteos mínimos?
   ?- caso1:ranking_sospecha(R).   % ¿el orden es el que querías?
   ?- caso1:responsable(P).        % debe dar UNA sola respuesta
   ```
4. Cuando tu caso responda, aparece solo en la interfaz y en `/admin`. No hay
   que registrar nada en ningún lado.
5. Activá tus filas en la plantilla de `tests/test_prolog_integracion.py`.

**Si te toca el backend (`backend/app/main.py`)**

Buscá los `TODO(backend)`. Los endpoints ya consultan Prolog; lo que falta es la
capa de encima: descubrimiento progresivo de la información, bitácora de
investigación e informe final del caso.

Si necesitás un dato que Prolog no expone, agregá un predicado `api_*` plano en
`prolog/logic_detective.pl`. No desarmes términos de Prolog en Python ni metas
decisiones en Python.

**Si te toca la interfaz (`frontend/`)**

Buscá los `TODO(interfaz)`. Falta el flujo de acciones de investigación en
`caso.html`, la bitácora y el historial en `admin.html`, y el diseño.

Estas dos partes van de la mano: el flujo de acciones y la bitácora necesitan
endpoints nuevos. Acuerden la forma de esos endpoints entre backend e interfaz
**antes** de empezar a programarlos, o uno va a quedar esperando al otro.

**Reglas base (`prolog/reglas_base.pl`)**

No la edites por tu cuenta: los tres casos la incluyen y un cambio ahí los
afecta a todos. Si te falta un predicado, hablá con el coordinador.

## Flujo de trabajo con Git

Dos ramas fijas y una rama por tarea:

```
main        entregable estable. Solo recibe merges desde develop.
develop     integración. Aquí se juntan los aportes de todos.
feat/...    una rama por tarea, sale de develop y vuelve por pull request.
```

Nombres de rama sugeridos, uno por responsabilidad:

```
feat/caso1        feat/caso2        feat/caso3
feat/backend      feat/interfaz     docs/manuales
```

**Cómo trabajar tu parte**

```bash
git switch develop && git pull
git switch -c feat/caso1          # tu rama
# ... trabajás y hacés tus commits ...
git push -u origin feat/caso1     # abrís el pull request hacia develop
```

Trabajá siempre en tu rama, nunca directo en `main`. Como cada caso es un
archivo distinto y un módulo Prolog aparte, en la práctica no deberían darse
conflictos entre ustedes.

**Mensajes de commit**

Prefijo, dos puntos y qué hiciste, en minúsculas:

```
feat(prolog): agregar los 10 hechos de evidencia del caso 1
fix(prolog): corregir la coartada de la sospechosa 3
test: activar los casos de prueba del caso 1
docs: manual de usuario del módulo de investigación
```

Prefijos que usamos: `feat`, `fix`, `test`, `docs`, `ci`, `refactor`, `chore`.

Cada quien hace sus propios commits con su cuenta: son la evidencia con la que
se respaldan los porcentajes de participación del informe.

**Etiquetas de versión**

Una etiqueta por entrega, para que quede un punto exacto al que volver:

```bash
git tag -a v1.0.0 -m "Entrega final del proyecto 1"
git push origin v1.0.0
```

| Etiqueta | Qué marca |
| --- | --- |
| `v0.1.0` | Esqueleto: estructura, reglas base, integración, Docker y CI |
| `v1.0.0` | Entrega final, con los tres casos completos |

## División del trabajo

Grupo 15. Coordinador: Henrry Omar Martínez Charuc.

| | Carné | Integrante | Rol |
| --- | --- | --- | --- |
| P1 | 201708845 | Joshua Estuardo Franco Equite | Prolog — Caso 1 |
| P2 | 201700312 | Aybson Diddiere Mercado Grijalva | Prolog — Caso 2 |
| P3 | 202100039 | Madeline Fabiola Prado Reyes | Prolog — Caso 3 |
| P4 | 9622440 | Henrry Omar Martínez Charuc | Backend Python + integración PySwip. Coordinación |
| P5 | 201020600 | Pedro Alexander Salazar Pocasangre | Interfaz + Docker/CI-CD/Despliegue |

Los 10 casos de prueba los escribe el dueño de cada caso: tres cada uno, ya
repartidos en la plantilla de `tests/test_prolog_integracion.py`.

El cronograma semana a semana y los porcentajes están en
[`docs/DISTRIBUCION_TRABAJO.md`](docs/DISTRIBUCION_TRABAJO.md).

## Estado

Listo y funcionando: la estructura, las reglas base en Prolog, el backend con
PySwip, el esqueleto de la interfaz con sus dos módulos, los contenedores y el
CI. Todo el camino interfaz -> backend -> Prolog está probado de punta a punta.

Pendiente: los tres casos de investigación, los 10 casos de prueba, el
descubrimiento progresivo de la información, la bitácora, el informe final del
caso, el diseño visual, la documentación y el despliegue en la VM. Los `TODO` en
el código marcan cada cosa.
