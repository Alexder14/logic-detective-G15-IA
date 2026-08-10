# Roles, cronograma y distribución del trabajo

**Curso:** Inteligencia Artificial 1 · **Sección:** A
**Proyecto:** 1 — Logic Detective · **Grupo:** 15
**Coordinador:** Henrry Omar Martínez Charuc
**Elaboración:** 31/07 – 28/08/2026 · **Calificación:** 29/08/2026

## Roles

| | Carné | Nombre | Rol |
| --- | --- | --- | --- |
| P1 | 202100039 | Madeline Fabiola Prado Reyes | Prolog — Caso 1 (hechos, reglas, consultas) |
| P2 | 201700312 | Aybson Diddiere Mercado Grijalva | Prolog — Caso 2 (hechos, reglas, consultas) |
| P3 | 201708845 | Joshua Estuardo Franco Equite | Prolog — Caso 3 (hechos, reglas, consultas) |
| P4 | 9622440 | Henrry Omar Martínez Charuc | Backend Python + integración PySwip. Coordinación |
| P5 | 201020600 | Pedro Alexander Salazar Pocasangre | Interfaz + Docker/CI-CD/Despliegue |

Correos: 3031289330108, 1817571250101, 2989023540101, 1856401410101 y
3942784100101, todos en `@ingenieria.usac.edu.gt`.

### Los 10 casos de prueba

Los escribe **el dueño de cada caso**: tres cada uno, más uno de ejemplo ya
resuelto. Están repartidos así en la plantilla de
`tests/test_prolog_integracion.py`, solo hay que quitarles el `skip`.

Se cambió respecto del plan original, donde los 10 los armaba P3. Dos razones:
P3 quedaba con su caso más las pruebas de los otros dos, y quien no escribió un
caso no sabe qué debería responder. Si el grupo prefiere volver al plan
original, es cambiar quién quita los `skip`.

## Cronograma

### Semana 1 · 03–07 ago

| P1, P2, P3 — Prolog | P4 — Backend | P5 — Interfaz e infra |
| --- | --- | --- |
| Reunión conjunta: revisar los predicados y reglas base ya escritos en `prolog/reglas_base.pl`. Cada quien empieza a modelar sospechosos y hechos de su caso. | Revisar el contrato de consultas que ya expone el motor (los predicados `api_*`) y decidir qué falta para el descubrimiento progresivo y la bitácora. | **Hecho:** repositorio, estructura, convención de commits, esqueleto de la interfaz. |

El esqueleto se adelantó: la API ya consulta Prolog de verdad, sin datos mock, y
`docker-compose up --build` levanta el sistema completo. Eso libera a P4 y P5 de
buena parte de las semanas 1 y 2.

### Semana 2 · 08–15 ago

| P1, P2, P3 — Prolog | P4 — Backend | P5 — Interfaz e infra |
| --- | --- | --- |
| Cada quien puebla su caso: evidencias, declaraciones y mínimo 10 reglas de inferencia propias. | Descubrimiento progresivo: filtrar lo ya examinado, interrogar de a una declaración, entregar las pistas de a una. | Flujo de acciones de investigación en `caso.html`, contra los endpoints de P4. |

### Semana 3 · 16–22 ago

| P1, P2, P3 — Prolog | P4 — Backend | P5 — Interfaz e infra |
| --- | --- | --- |
| Cierran los 3 casos completos. Prueban las consultas en SWI-Prolog antes de entregarlas: `?- casoN:responsable(P).` debe dar una sola respuesta. | Bitácora de investigación e informe final del caso. Pruebas de la API. | Vista de la bitácora y el historial en `admin.html`. Diseño visual. |

### Semana 4 · 23–28 ago

| P1, P2, P3 — Prolog | P4 — Backend | P5 — Interfaz e infra |
| --- | --- | --- |
| Cada quien activa sus 3 casos de prueba y corrige lo que falle. Meta: 80 % de aciertos. | Pruebas finales end-to-end. Corrige bugs de integración. | Despliegue en AWS/GCP. Documentación técnica y de usuario. Diagramas. |

**29 ago:** calificación.

## Entregable clave por semana

| Semana | Debe quedar listo |
| --- | --- |
| 1 | Reglas base revisadas, roles con nombre y fechas acordadas. Repositorio creado. |
| 2 | Los 3 casos con hechos y reglas mínimas. Descubrimiento progresivo funcionando. |
| 3 | Los 3 casos completos. Bitácora e informe final. Docker Compose corriendo. |
| 4 | Pruebas ≥ 80 %. Desplegado en la nube. Documentación e informe de participación. |

Cómo verificar el avance de los casos en cualquier momento:

```bash
swipl -q -g "consult('prolog/logic_detective.pl'), \
  forall(api_caso(M,_,_,_,_,E,NS,NE,NL,ND), \
    format('~w: ~w (~w/4 sosp, ~w/10 evid, ~w/5 lug, ~w/5 decl)~n', \
      [M,E,NS,NE,NL,ND])), halt"
```

También sale en la interfaz, en el módulo administrativo.

## Participación

Los porcentajes deben sumar 100 % y estar respaldados por commits.

| Carné | Nombre | Actividades | Usuario GitHub | % |
| --- | --- | --- | --- | --- |
| 202100039 | Madeline Fabiola Prado Reyes | Caso 1 en Prolog, sus 3 casos de prueba y su sección del manual técnico | | 20 % |
| 201700312 | Aybson Diddiere Mercado Grijalva | Caso 2 en Prolog, sus 3 casos de prueba y su sección del manual técnico | | 20 % |
| 201708845 | Joshua Estuardo Franco Equite | Caso 3 en Prolog, sus 3 casos de prueba y su sección del manual técnico | | 20 % |
| 9622440 | Henrry Omar Martínez Charuc | Backend: descubrimiento progresivo, bitácora e informe final. Coordinación del grupo e informe de participación | | 20 % |
| 201020600 | Pedro Alexander Salazar Pocasangre | Estructura del repositorio, reglas base en Prolog, integración con PySwip, interfaz completa, Docker, CI/CD, despliegue y documentación | | 20 % |
| | | | **TOTAL** | **100 %** |

## Evidencias de respaldo

Falta la columna de usuario de GitHub: es lo que permite atribuir los commits.

```bash
git log --author="usuario" --oneline
```

Cada quien hace sus propios commits con su cuenta y trabaja en su rama
(`feat/caso1`, `feat/caso2`, `feat/caso3`, `feat/backend`, `feat/interfaz`). El
flujo de ramas está en el README.

## Incidencias

Ninguna al momento. Registrar aquí cualquier incumplimiento, abandono o
conflicto que deba reportarse al tutor.
