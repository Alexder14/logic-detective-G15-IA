# =============================================================================
#  Frontend: Flask + Jinja2
# =============================================================================
#  No necesita Prolog: todo lo consulta al backend por HTTP.
#
#  El contexto de build es la RAÍZ del repositorio, igual que el backend, para
#  que los dos servicios se construyan con el mismo docker-compose.

FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY frontend/requirements.txt /app/frontend/requirements.txt
RUN pip install --no-cache-dir -r /app/frontend/requirements.txt

COPY frontend/ /app/frontend/

RUN useradd --create-home --uid 1000 detective \
    && chown -R detective:detective /app
USER detective

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -fsS http://localhost:8080/salud || exit 1

# gunicorn en lugar del servidor de desarrollo de Flask. Con 2 workers alcanza,
# esta capa solo reenvía peticiones.
CMD ["gunicorn", \
     "--chdir", "/app/frontend", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--access-logfile", "-", \
     "app:app"]
