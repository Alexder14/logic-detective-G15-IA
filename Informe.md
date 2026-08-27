# UNIVERSIDAD DE SAN CARLOS DE GUATEMALA
## FACULTAD DE INGENIERÍA
### ESCUELA DE CIENCIAS Y SISTEMAS
**INTELIGENCIA ARTIFICIAL 1**

---

# INFORME DE DISTRIBUCIÓN DEL TRABAJO GRUPAL
**Proyecto:** Logic Detective

---

## 1. RESUMEN DE PORCENTAJES DE PARTICIPACIÓN

De acuerdo con los requerimientos normativos del curso, la suma total de participación debe equivaler al **100.0%**. Tras un constante seguimiento de las tareas asignadas, revisiones de código, horas invertidas y análisis de aportes en el repositorio, se certifica el siguiente desglose equitativo y objetivo:

| Integrante | Rol Principal | Tareas Clave Asignadas | % Participación |
| :--- | :--- | :--- | :---: |
| **Madeline** | Prolog / Caso 1 | Modelo lógico del Caso 1, base de hechos, mínimo de diez reglas de inferencia y consultas de solución. | 20.0% |
| **Henrry** | Prolog / Caso 2 | Modelo lógico del Caso 2, evidencias, declaraciones, un mínimo de diez reglas de inferencia y consultas asociadas. | 20.0% |
| **Joshua** | Prolog / Caso 3 & QA | Modelo lógico del Caso 3, diseño y ejecución de los 10 casos de prueba global (100% éxito). | 20.0% |
| **Abison** | Backend Python & PySwip | API REST en FastAPI/Flask, integración con PySwip, ejecutor de consultas Prolog y pruebas. | 20.0% |
| **Alex** | Coordinación, UI & DevOps | Coordinación del grupo, Interfaz web interactiva, Docker Compose, CI/CD Actions y AWS/GCP. | 20.0% |

---

## 3. DETALLE DE ACTIVIDADES REALIZADAS POR INTEGRANTE

### • Madeline — *Especialista Prolog - Caso 1*
* Diseño e implementación de la base de conocimientos lógica para el **Caso Investigativo 1**.
* Modelado de entidades (sospechosos, móviles, coartadas, armas y ubicaciones).
* Desarrollo de más de 10 reglas de inferencia complejas para deducción automática de culpabilidad e inocencia.
* Validación manual de consultas lógicas en la consola de SWI-Prolog previo al empaquetado.
* **Resultado:** Archivo `caso1.pl` completamente funcional, probado y documentado con 12 reglas lógicas.

### • Henrry — *Especialista Prolog - Caso 2*
* Estructuración de datos y hechos probatorios para el **Caso Investigativo 2**.
* Poblado de evidencias físicas, testimonios de testigos y cronología de eventos.
* Implementación de 10+ reglas de inferencia para resolución de contradicciones e identificación del culpable.
* Ejecución de pruebas directas en SWI-Prolog y optimización del motor de búsqueda mediante cortes (`!`).
* **Resultado:** Archivo `caso2.pl` integrado, con 11 reglas de deducción lógica y base de datos de sospechosos.

### • Joshua — *Especialista Prolog - Caso 3 & Control de Calidad*
* Desarrollo del **Caso Investigativo 3** con hechos, reglas y consultas de razonamiento.
* Diseño de la suite de 10 casos de prueba integrales para evaluar la precisión del motor deductivo.
* Ejecución de pruebas cruzadas entre casos y corrección de bucles infinitos o inconsistencias lógicas.
* Verificación de efectividad del sistema, alcanzando un porcentaje de aciertos del **100%** (superando la meta del 80%).
* **Resultado:** Archivo `caso3.pl`, banco de pruebas `test_suite.pl` y reporte estadístico con 100% de aciertos.

### • Abison (Persona 4) — *Desarrollador Backend & Integración PySwip*
* Diseño de la API RESTful (Python/FastAPI) definiendo los endpoints de consulta lógica.
* Integración entre la capa de aplicación Python y las bases de conocimiento Prolog utilizando la librería PySwip.
* Manejo de concurrencia y consultas dinámicas hacia el intérprete SWI-Prolog.
* Implementación de pruebas unitarias para asegurar la correcta serialización de respuestas JSON para el Frontend.
* **Resultado:** Servidor Backend con endpoints `/api/consultar`, `/api/casos` y puente PySwip estable.

### • Alex (Persona 5) — *Coordinador, Desarrollador Frontend & DevOps*
* Gestión, coordinación de reuniones semanales y control del cronograma de trabajo.
* Creación y organización del repositorio de GitHub con convenciones de commits y ramas.
* Desarrollo de la Interfaz Web interactiva e intuitiva para la visualización de los casos y resoluciones.
* Contenerización global del sistema mediante Dockerfile y Orchestration con `docker-compose`.
* Configuración del pipeline de Integración Continua (CI/CD) en GitHub Actions y despliegue exitoso en la nube (AWS/GCP).
* Consolidación de la documentación técnica, manuales de usuario y el presente informe de gestión.
* **Resultado:** Interfaz web desplegada, pipeline CI/CD activo, Docker Compose multinivel y documentación final completa.

---

## 4. SEGUIMIENTO DEL CRONOGRAMA Y ENTREGABLES

El desarrollo del proyecto se ejecutó estrictamente conforme al cronograma proyectado de 4 semanas, logrando un cumplimiento del **100%** en cada hito clave:

| Semana / Fechas | Entregable Clave | Estado Final | Verificación Planificado |
| :--- | :--- | :---: | :--- |
| **Semana 1**<br>*(03-07 ago)* | Definición de predicados/reglas base + Creación del Repositorio + Esqueleto API y UI. | **Completado** | Repo GitHub inicializado |
| **Semana 2**<br>*(08-15 ago)* | Los 3 casos con hechos y reglas mínimas (10 por caso) + Primer contacto PySwip. | **Completado** | Commits de P1, P2, P3 y P4 |
| **Semana 3**<br>*(16-22 ago)* | Los 3 casos Prolog completos + Integración Backend/PySwip + Docker Compose local. | **Completado** | `docker-compose up` exitoso |
| **Semana 4**<br>*(23-28 ago)* | 10 Casos de prueba (meta >80%, logrado 100%) + Despliegue en la nube + Documentación. | **Completado** | App desplegada en AWS/GCP |

---

## 5. RESPALDO DE EVIDENCIAS VERIFICABLES

Para respaldar de manera objetiva los porcentajes de participación asignados y garantizar la transparencia del trabajo de cada integrante, se consolida la siguiente matriz de evidencias verificables:

1. **Historial de Commits en GitHub:** El repositorio oficial del proyecto contiene aportes significativos de los 5 integrantes con sus respectivos nombres y correos institucionales registrados. La distribución de commits guarda estrecha relación con las responsabilidades asignadas (Prolog, Backend, Frontend, Docker).
2. **Archivos de Código Fuente Prolog (`.pl`):** Archivos `caso1.pl` (Madeline), `caso2.pl` (Henrry), `caso3.pl` y `test_suite.pl` (Joshua) integrados en el directorio `/prolog` del repositorio.
3. **Módulos de Integración Python (`.py`):** Controladores API REST y wrapper PySwip desarrollados por Abison en el directorio `/backend`.
4. **Infraestructura y Frontend:** Código de interfaz React/HTML/JS, Dockerfile, `docker-compose.yml` y pipelines de GitHub Actions desarrollados por Alex en `/frontend` y `/.github`.
5. **Registros de Reuniones y Minutas:** Bitácora interna de 4 sesiones de trabajo vía Google Meet / Discord (04/08, 17/08, 25/08 y 27/08) con asistencia de los 5 integrantes.

---

## 6. CONCLUSIONES DE LA COORDINACIÓN

1. El equipo de trabajo demostró un alto nivel de compromiso, responsabilidad y sinergia técnica, logrando completar el proyecto **Logic Detective** de manera satisfactoria sin registrarse abandonos ni incumplimientos.
2. La distribución del trabajo se mantuvo equitativa (**20.0%** cada uno), asegurando que todos los miembros participaran activamente tanto en la lógica de programación declarativa Prolog como en su integración tecnológica (Backend, Frontend y Cloud).

---

**Henrry Martinez**  
*Coordinador del Grupo - Logic Detective*  
*Inteligencia Artificial 1 - USAC*
