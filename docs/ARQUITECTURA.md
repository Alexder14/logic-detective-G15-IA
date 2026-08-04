# Arquitectura del sistema

> PLACEHOLDER — completar durante el desarrollo.
> Responsable: coordinador. Entregable de la rúbrica: "Diagramas arquitectónicos"
> y "Diagrama de Flujo" (10 pts de Documentación).

## 1. Vista de componentes

Pendiente: diagrama de los tres componentes (frontend, backend, motor Prolog) y
sus protocolos de comunicación. Base en el diagrama ASCII del `README.md`.

## 2. Flujo de una consulta

Pendiente: diagrama de secuencia de, por ejemplo,
`GET /api/casos/caso1/conclusion`:

1. El navegador pide la vista al frontend Flask.
2. Flask llama al backend FastAPI por HTTP.
3. FastAPI arma la meta Prolog y la ejecuta con PySwip.
4. SWI-Prolog resuelve por unificación/backtracking sobre `reglas_base.pl`.
5. Las soluciones vuelven como diccionarios de Python y se serializan a JSON.

## 3. Modelo de la base de conocimiento

Pendiente: tabla de los predicados de hechos (ver encabezado de
`prolog/reglas_base.pl`) y grafo de dependencia entre reglas derivadas.

## 4. Decisiones de diseño

Pendiente: documentar por qué cada caso es un módulo Prolog independiente y por
qué las reglas se incluyen textualmente con `:- include/1`.

## 5. Despliegue

Pendiente: diagrama del despliegue en la VM (AWS/GCP), puertos y variables de
entorno.
