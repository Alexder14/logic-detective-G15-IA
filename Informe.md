# UNIVERSIDAD DE SAN CARLOS DE GUATEMALA
## FACULTAD DE INGENIERÍA
### ESCUELA DE CIENCIAS Y SISTEMAS
**INTELIGENCIA ARTIFICIAL 1**

---

# INFORME DE DISTRIBUCIÓN DEL TRABAJO GRUPAL
**Proyecto:** 1 — Logic Detective · **Grupo:** 15 · **Sección:** A
**Coordinador:** Henrry Omar Martínez Charuc (199622440)
**Repositorio:** https://github.com/Alexder14/logic-detective-G15-IA
**Sistema desplegado:** http://34.121.98.65:8080

---

## 1. RESUMEN DE PORCENTAJES DE PARTICIPACIÓN

De acuerdo con los requerimientos normativos del curso, la suma total de participación debe equivaler al **100.0%**. Tras un constante seguimiento de las tareas asignadas, revisiones de código, horas invertidas y análisis de aportes en el repositorio, se certifica el siguiente desglose equitativo y objetivo:

| Carné | Integrante | Usuario GitHub | Rol Principal | Tareas Clave Asignadas | % Participación |
| :--- | :--- | :--- | :--- | :--- | :---: |
| 202100039 | **Madeline Fabiola Prado Reyes** | MadelinePrado | Prolog / Caso 1 | Modelo lógico del Caso 1, base de hechos, dieciséis reglas de inferencia propias y consultas de solución. | 20.0% |
| 199622440 | **Henrry Omar Martínez Charuc** | henrrymartinez | Prolog / Caso 2 y coordinación | Modelo lógico del Caso 2, evidencias, declaraciones, diez reglas de inferencia propias y consultas asociadas. Coordinación del grupo e informe de participación. | 20.0% |
| 201708845 | **Joshua Estuardo Franco Equite** | JoshF8 | Prolog / Caso 3 y QA | Modelo lógico del Caso 3 con once reglas propias, diseño y ejecución de los 10 casos de prueba del curso. | 20.0% |
| 201700312 | **Aybson Diddiere Mercado Grijalva** | Aybson Mercado | Backend Python & PySwip | API REST en FastAPI, integración con PySwip, descubrimiento progresivo, bitácora e informe final del caso. | 20.0% |
| 201020600 | **Pedro Alexander Salazar Pocasangre** | Alexder14 | Interfaz, DevOps y despliegue | Interfaz web en Flask + Jinja2, reglas base en Prolog, Docker Compose, CI/CD en GitHub Actions y despliegue en GCP. | 20.0% |

---

## 2. DETALLE DE ACTIVIDADES REALIZADAS POR INTEGRANTE

### • Madeline Prado (202100039) — *Especialista Prolog - Caso 1*
* Diseño e implementación de la base de conocimientos lógica para el **Caso Investigativo 1**.
* Modelado de entidades (sospechosos, móviles, coartadas, armas y ubicaciones).
* Desarrollo de más de 10 reglas de inferencia complejas para deducción automática de culpabilidad e inocencia.
* Validación manual de consultas lógicas en la consola de SWI-Prolog previo al empaquetado.
* **Resultado:** Archivo `caso1.pl` completamente funcional, probado y documentado con 16 reglas de inferencia propias.

### • Henrry Martínez (199622440) — *Especialista Prolog - Caso 2*
* Estructuración de datos y hechos probatorios para el **Caso Investigativo 2**.
* Poblado de evidencias físicas, testimonios de testigos y cronología de eventos.
* Implementación de 10+ reglas de inferencia para resolución de contradicciones e identificación del culpable.
* Ejecución de pruebas directas en SWI-Prolog y optimización del motor de búsqueda mediante cortes (`!`).
* **Resultado:** Archivo `caso2.pl` integrado, con 10 reglas de inferencia propias y su base de hechos de sospechosos.

### • Joshua Franco (201708845) — *Especialista Prolog - Caso 3 & Control de Calidad*
* Desarrollo del **Caso Investigativo 3** con hechos, reglas y consultas de razonamiento.
* Diseño de la suite de 10 casos de prueba integrales para evaluar la precisión del motor deductivo.
* Ejecución de pruebas cruzadas entre casos y corrección de bucles infinitos o inconsistencias lógicas.
* Verificación de efectividad del sistema, alcanzando un porcentaje de aciertos del **100%** (superando la meta del 80%).
* **Resultado:** Archivo `caso3.pl` con 11 reglas de inferencia propias y los 10 casos de prueba del curso en `tests/test_prolog_integracion.py`, todos en verde.

### • Aybson Mercado (201700312) — *Desarrollador Backend & Integración PySwip*
* Diseño de la API RESTful (Python/FastAPI) definiendo los endpoints de consulta lógica.
* Integración entre la capa de aplicación Python y las bases de conocimiento Prolog utilizando la librería PySwip.
* Manejo de concurrencia y consultas dinámicas hacia el intérprete SWI-Prolog.
* Implementación de pruebas unitarias para asegurar la correcta serialización de respuestas JSON para el Frontend.
* **Resultado:** Servidor FastAPI con los endpoints `/api/casos`, `/api/casos/{caso_id}/sospechosos`, `/api/casos/{caso_id}/contradicciones`, `/api/casos/{caso_id}/acusacion` y `/api/admin/estado`, sobre un puente PySwip estable.

### • Pedro Alexander Salazar (201020600) — *Coordinador, Desarrollador Frontend & DevOps*
* Gestión, coordinación de reuniones semanales y control del cronograma de trabajo.
* Creación y organización del repositorio de GitHub con convenciones de commits y ramas.
* Desarrollo de la Interfaz Web interactiva e intuitiva para la visualización de los casos y resoluciones.
* Contenerización global del sistema mediante Dockerfile y Orchestration con `docker-compose`.
* Configuración de los pipelines de CI y CD en GitHub Actions —con autenticación por Workload Identity Federation— y despliegue en una VM de Google Cloud Platform, accesible en http://34.121.98.65:8080.
* Consolidación de la documentación técnica, manuales de usuario y el presente informe de gestión.
* **Resultado:** Interfaz web desplegada, pipeline CI/CD activo, Docker Compose multinivel y documentación final completa.

---

## 3. SEGUIMIENTO DEL CRONOGRAMA Y ENTREGABLES

El desarrollo del proyecto se ejecutó estrictamente conforme al cronograma proyectado de 4 semanas, logrando un cumplimiento del **100%** en cada hito clave:

| Semana / Fechas | Entregable Clave | Estado Final | Verificación Planificado |
| :--- | :--- | :---: | :--- |
| **Semana 1**<br>*(03-07 ago)* | Definición de predicados/reglas base + Creación del Repositorio + Esqueleto API y UI. | **Completado** | Repo GitHub inicializado |
| **Semana 2**<br>*(08-15 ago)* | Los 3 casos con hechos y reglas mínimas (10 por caso) + Primer contacto PySwip. | **Completado** | Commits de P1, P2, P3 y P4 |
| **Semana 3**<br>*(16-22 ago)* | Los 3 casos Prolog completos + Integración Backend/PySwip + Docker Compose local. | **Completado** | `docker-compose up` exitoso |
| **Semana 4**<br>*(23-28 ago)* | 10 Casos de prueba (meta >80%, logrado 100%) + Despliegue en la nube + Documentación. | **Completado** | App desplegada en GCP: http://34.121.98.65:8080 |

---

## 4. RESPALDO DE EVIDENCIAS VERIFICABLES

Para respaldar de manera objetiva los porcentajes de participación asignados y garantizar la transparencia del trabajo de cada integrante, se consolida la siguiente matriz de evidencias verificables:

1. **Historial de Commits en GitHub:** El repositorio oficial del proyecto contiene aportes significativos de los 5 integrantes con sus respectivos nombres y correos institucionales registrados. La distribución de commits guarda estrecha relación con las responsabilidades asignadas (Prolog, Backend, Frontend, Docker).
2. **Archivos de Código Fuente Prolog (`.pl`):** Archivos `caso1.pl` (Madeline), `caso2.pl` (Henrry) y `caso3.pl` (Joshua) en el directorio `/prolog`, sobre las reglas compartidas de `reglas_base.pl`. Los 10 casos de prueba de Joshua están en `tests/test_prolog_integracion.py`.
3. **Módulos de Integración Python (`.py`):** Controladores API REST y wrapper PySwip desarrollados por Aybson Mercado en el directorio `/backend`.
4. **Infraestructura y Frontend:** Interfaz en Flask + Jinja2 y CSS propio, Dockerfile de cada servicio, `docker-compose.yml`, los pipelines de GitHub Actions y los scripts de despliegue, desarrollados por Pedro Alexander en `/frontend`, `/.github` y `/deploy`.
5. **Registros de Reuniones y Minutas:** Bitácora interna de 4 sesiones de trabajo vía Google Meet / Discord (04/08, 17/08, 25/08 y 27/08) con asistencia de los 5 integrantes.

---

## 5. CONCLUSIONES DE LA COORDINACIÓN

1. El equipo de trabajo demostró un alto nivel de compromiso, responsabilidad y sinergia técnica, logrando completar el proyecto **Logic Detective** de manera satisfactoria sin registrarse abandonos ni incumplimientos.
2. La distribución del trabajo se mantuvo equitativa (**20.0%** cada uno), asegurando que todos los miembros participaran activamente tanto en la lógica de programación declarativa Prolog como en su integración tecnológica (Backend, Frontend y Cloud).

---

**Henrry Omar Martínez Charuc** (199622440)  
*Coordinador del Grupo - Logic Detective*  
*Inteligencia Artificial 1 - USAC*
