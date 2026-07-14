# Workshop No. 1 — Requirements, User Stories & Story Mapping

**Proyecto:** SpyNet — *Watching every part | Auditing every weakness*  
**Grupo 5:** Los Extraditables  
**Curso:** Ingeniería de Software II — Universidad Nacional de Colombia  
**Repositorio:** [github.com/jdrsajonia/spynet](https://github.com/jdrsajonia/spynet)

---

## Integrantes y roles

La siguiente distribución corresponde a la asignación consolidada del equipo y debe mantenerse igual en todos los documentos del proyecto.

| Integrante | Rol principal |
|---|---|
| Juan Diego Rozo Álvarez | Backend |
| Santiago Alejandro Rojas Feo | Backend |
| Alejandro Medina Rojas | Backend |
| Misael Jesus Flores Anave | DevOps |
| Cristian David Arcia Quintero | Frontend |
| Marlon David Pabon Muñoz | CI/CD y documentación |

> **Nota de consistencia:** esta tabla reemplaza la asignación preliminar del Workshop 1. También normaliza el apellido **Flores** y conserva la distribución presentada en el Workshop 2.

---

## Acerca de SpyNet

SpyNet es una aplicación web de análisis tecnológico y auditoría pasiva que permite investigar la composición técnica de un sitio a partir de una URL. El sistema combina un backend en Django REST Framework, una interfaz en React y una base de datos PostgreSQL para recolectar, organizar, persistir y presentar información sobre:

- tecnologías frontend y backend;
- servidores web, CDN y servicios de analítica;
- registros DNS y configuración de correo;
- información WHOIS;
- geolocalización y datos de red;
- certificados TLS/SSL;
- postura pasiva de seguridad con calificación global de **A a F**;
- snapshots históricos de Wayback Machine;
- evolución de tecnologías a través del tiempo;
- comparación entre análisis;
- estadísticas agregadas;
- consultas en lenguaje natural mediante Google Gemini, con respaldo local basado en reglas.

El principio de seguridad de SpyNet es estrictamente **pasivo**: la auditoría utiliza datos obtenidos durante el análisis normal y no ejecuta pruebas de intrusión, explotación de vulnerabilidades ni escaneos agresivos.

---

## Estado documental consolidado

El alcance original del Workshop 1 creció conforme avanzó la implementación. Esta versión del README refleja el alcance consolidado que debe incorporarse al documento corregido.

| Artefacto | Versión inicial | Alcance consolidado | Total |
|---|---:|---:|---:|
| Requisitos funcionales | RF-01 a RF-14 | RF-01 a RF-26 | **26** |
| Requisitos no funcionales | RNF-01 a RNF-08 | RNF-01 a RNF-09 | **9** |
| Reglas de negocio | RN-01 a RN-09 | RN-01 a RN-12 | **12** |
| Historias de usuario | US-01 a US-11 | US-01 a US-22 | **22** |
| Planeación | 3 sprints | 3 sprints actualizados | **3** |

Los nuevos artefactos documentan capacidades que ya forman parte del producto: auditoría de seguridad, inspección TLS, seguridad de correo, detección de analítica, documentación interactiva de la API, vista Home y asistente de IA contextual.

---

## Contenido del Workshop 1

### 1. Requisitos funcionales y no funcionales

La especificación consolidada contiene **26 requisitos funcionales** (`RF-01` a `RF-26`) y **9 requisitos no funcionales** (`RNF-01` a `RNF-09`).

Los requisitos incorporados en la última ampliación son:

| ID | Capacidad |
|---|---|
| RF-21 | Auditoría pasiva de postura de seguridad con nota A–F y hallazgos por severidad |
| RF-22 | Inspección del certificado TLS/SSL y de su vigencia |
| RF-23 | Evaluación informativa de SPF, DMARC y DNSSEC |
| RF-24 | Detección de servicios de analítica y seguimiento |
| RF-25 | Documentación OpenAPI interactiva, pruebas desde navegador y ejemplos cURL |
| RF-26 | Vista Home como punto de entrada al producto |
| RNF-09 | Generación automática de la documentación de API mediante drf-spectacular |

El `RNF-05` debe registrar además el resultado alcanzado por el proyecto: **81 % de cobertura reportada con 84 pruebas en la medición documentada**.

### 2. Reglas de negocio

El documento corregido reúne **12 reglas de negocio** (`RN-01` a `RN-12`). Las tres reglas añadidas formalizan decisiones fundamentales de la implementación:

- **RN-10:** la nota de seguridad se calcula únicamente con información recolectada de forma pasiva;
- **RN-11:** la clave de Gemini permanece en el backend y el sistema usa un motor local si el proveedor no está disponible;
- **RN-12:** la ausencia de SPF, DMARC o DNSSEC produce un hallazgo informativo, no el fallo del análisis.

### 3. Historias de usuario

El backlog consolidado contiene **22 historias de usuario** (`US-01` a `US-22`) redactadas con criterios de aceptación **Given / When / Then**.

La ampliación final agrega:

| ID | Historia | Prioridad | Sprint |
|---|---|---|---|
| US-18 | Ver la postura de seguridad y sus hallazgos | Should have | Sprint 3 |
| US-19 | Inspeccionar el certificado TLS/SSL | Could have | Sprint 3 |
| US-20 | Consultar SPF, DMARC y DNSSEC | Could have | Sprint 3 |
| US-21 | Explorar y probar la API desde su documentación | Should have | Sprint 3 |
| US-22 | Conversar con el asistente de IA sobre un análisis | Should have | Sprint 3 |

### 4. User Story Mapping

El Story Map mantiene una planeación de **tres sprints**, pero amplía el mapa con dos actividades y una línea de trabajo actualizada:

1. **Seguridad y auditoría:** nota de seguridad, certificado TLS y seguridad del correo (`US-18` a `US-20`).
2. **Experiencia de desarrollador:** documentación interactiva de la API (`US-21`).
3. **Inteligencia artificial:** conversación contextual sobre los resultados, con Gemini y fallback local (`US-22`).

Las cinco historias nuevas corresponden al **Sprint 3**, pues representan funcionalidades implementadas durante la consolidación del producto.

---

## Trazabilidad con la implementación

El Workshop 1 no es una especificación aislada: sus requisitos e historias se relacionan directamente con componentes verificables del repositorio.

| Capacidad documentada | Evidencia principal en el repositorio |
|---|---|
| Orquestación del análisis | `analyzer.py` |
| Persistencia relacional | `api/models.py`, `api/persistence.py`, `api/migrations/` |
| API REST y validación | `api/views.py`, `api/urls.py`, `api/serializers/` |
| Auditoría pasiva A–F | `core/security_auditor.py` |
| Inspección TLS | `services/tls_service.py` |
| DNS, WHOIS, geolocalización y Wayback | `services/` |
| Detección frontend, backend, CDN, servidor y analítica | `detectors/` |
| Asistente Gemini y fallback local | `api/ai_assistant.py` |
| Documentación OpenAPI | `config/urls.py`, `frontend/src/views/ApiDocsView.jsx` |
| Vista de bienvenida | `frontend/src/views/HomeView.jsx` |
| Interfaz de análisis e IA | `frontend/src/views/AnalyseView.jsx`, `frontend/src/components/AiChatPanel.jsx` |
| Pruebas automatizadas | `tests/` |
| Integración continua | `.github/workflows/` |

---

## API implementada

La API usa el prefijo versionado **`/api/v1/`**. Las referencias antiguas a `/api/analyze/`, `/api/analyses/` o `/api/stats/` sin versión deben considerarse obsoletas.

| Método | Ruta | Propósito |
|---|---|---|
| `GET`, `POST` | `/api/v1/analyses/` | Listar análisis o ejecutar uno nuevo |
| `GET` | `/api/v1/analyses/<id>/` | Consultar el detalle persistido de un análisis |
| `POST` | `/api/v1/analyses/<id>/wayback/` | Obtener o ampliar datos históricos de un análisis |
| `POST` | `/api/v1/analyses/snapshot/` | Analizar un snapshot concreto |
| `POST` | `/api/v1/analyses/historical/` | Ejecutar análisis histórico |
| `GET`, `POST` | `/api/v1/analyses/compare/` | Comparar resultados |
| `GET` | `/api/v1/domains/<name>/analyses/` | Consultar el historial de un dominio |
| `GET` | `/api/v1/stats/` | Obtener estadísticas globales |
| `POST` | `/api/v1/ai-analyses/` | Consultar el asistente sobre un análisis |
| `GET` | `/api/v1/schema/` | Obtener la especificación OpenAPI |
| `GET` | `/api/v1/docs/` | Abrir Swagger UI |

> La API actual es pública y no requiere API key en el navegador. La clave de Gemini es una credencial interna del backend y no constituye un mecanismo de autenticación para consumir los endpoints.

---

## Arquitectura resumida

SpyNet sigue una arquitectura por capas que separa responsabilidades y facilita las pruebas:

1. **Frontend:** SPA en React + Vite con vistas Home, Analyse, Historical, Dashboard, Compare y API Docs.
2. **API:** Django REST Framework gestiona solicitudes, serialización, errores y contratos HTTP.
3. **Núcleo de análisis:** `analyzer.py` coordina servicios, detectores, auditoría y persistencia.
4. **Servicios externos:** adaptadores independientes consultan DNS, WHOIS, geolocalización, TLS y Wayback Machine.
5. **Detección:** estrategias especializadas identifican frontend, backend, CDN, servidor y analítica mediante firmas y evidencia.
6. **Datos:** PostgreSQL almacena dominios, análisis, tecnologías, registros e historial.
7. **IA:** el backend prepara el contexto y consulta Gemini; ante fallos, responde mediante reglas locales.

---

## Principios de calidad y seguridad

- **Trazabilidad:** cada tecnología incluye evidencia que explica su detección.
- **Tolerancia a fallos:** la caída de un servicio externo no debe invalidar todo el análisis.
- **Persistencia normalizada:** los resultados se almacenan mediante modelos relacionados y restricciones de integridad.
- **Seguridad por diseño:** las credenciales sensibles permanecen en variables de entorno del backend.
- **Auditoría responsable:** no se ejecutan ataques, explotación ni pruebas intrusivas.
- **Documentación sincronizada:** OpenAPI se deriva del código para reducir inconsistencias.
- **Portabilidad:** Docker Compose estandariza PostgreSQL, backend y frontend para desarrollo.
- **Verificación:** pytest y la integración continua validan servicios, detectores, API, auditoría y asistente.

---

## Documentos del workshop

- 📄 [Workshop 1 original](./spynet_workshop_1.pdf)
- 📄 [Workshop 1 corregido](./spynet_workshop_1_correccion.pdf)
- 📂 [Repositorio principal de SpyNet](https://github.com/jdrsajonia/spynet)
- 📘 [README general del proyecto](../../README.md)

---

## Criterio de actualización

Este README se considera la portada y guía de navegación del Workshop 1. Por tanto, sus nombres, roles, conteos, rutas y descripciones deben permanecer sincronizados con:

1. el documento corregido del Workshop 1;
2. el diseño presentado en el Workshop 2;
3. los modelos y endpoints implementados;
4. el README principal del repositorio;
5. el comportamiento observable de la aplicación.

Cuando cambie el alcance, no basta con modificar el total: también deben actualizarse la trazabilidad, el Story Map, la tabla MoSCoW y los enlaces relacionados.

---

**Última revisión documental:** julio de 2026  
**Estado:** alcance implementado y documentación consolidada.
