# =============================================================================
#  Backend: FastAPI + PySwip + SWI-Prolog
# =============================================================================
#  PySwip no trae Prolog, carga la libswipl del sistema. Por eso va
#  swi-prolog-nox, la variante sin interfaz gráfica.
#
#  Construir y correr solo el backend:
#      docker build -f backend/Dockerfile -t logic-detective-backend .
#      docker run --rm -p 8000:8000 logic-detective-backend
#
#  IMPORTANTE: el contexto de build es la RAÍZ del repositorio, no backend/,
#  porque la imagen necesita también prolog/.

FROM python:3.12-slim-bookworm

# swi-prolog-nox aporta la libswipl que PySwip carga por ffi. curl es para el
# HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        swi-prolog-nox \
        curl \
    && rm -rf /var/lib/apt/lists/*

# PySwip encuentra libswipl.so preguntándole a swipl dónde está su home.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Las dependencias van antes que el código para reusar la capa de pip mientras
# requirements.txt no cambie.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# La base de conocimiento y el código de la API.
COPY prolog/ /app/prolog/
COPY backend/ /app/backend/

# Falla el build si la base de conocimiento no compila o si PySwip no puede
# cargar libswipl, en vez de fallar con el contenedor ya corriendo.
RUN swipl -q -g "consult('/app/prolog/logic_detective.pl'), halt" -t "halt(1)" \
    && python -c "\
from pyswip import Prolog; \
p = Prolog(); \
p.consult('/app/prolog/logic_detective.pl'); \
assert list(p.query('caso_modulo(caso1)')), 'la fachada Prolog no responde'; \
print('PySwip + SWI-Prolog OK')"

# No correr como root.
RUN useradd --create-home --uid 1000 detective \
    && chown -R detective:detective /app
USER detective

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Un solo worker: SWI-Prolog se carga en el proceso y no se comparte entre
# procesos. Para escalar hay que levantar más réplicas del contenedor.
CMD ["uvicorn", "app.main:app", \
     "--app-dir", "/app/backend", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1"]
