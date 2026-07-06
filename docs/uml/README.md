# UML Class Diagrams

## Purpose
El diagrama de clases original era demasiado grande para insertarse en un documento vertical estándar. Este archivo divide la arquitectura completa en varias vistas más pequeñas y manejables, manteniendo toda la jerarquía, relaciones y componentes principales del proyecto, sin perder información crítica.

## Render Instructions
Cada bloque de código contenido en este documento está escrito en formato PlantUML. Para visualizarlos:
1. Copia el bloque completo (desde `@startuml` hasta `@enduml`).
2. Pégalo en un archivo con extensión `.puml` en Visual Studio Code.
3. Renderízalo usando la extensión **PlantUML**.

## Recommended Order for Google Docs
Para incluir estos diagramas en tu documento vertical de manera lógica, se recomienda este orden:
1. General Class Overview
2. Analyzer Orchestration
3. Detectors Hierarchy
4. Services Hierarchy
5. Core Components
6. Modules / Utility Functions
7. Complete Class Diagram - Simplified Methods

---

## 1. General Class Overview

```plantuml
@startuml
title General Class Overview

top to bottom direction

skinparam backgroundColor white
skinparam packageStyle rectangle
skinparam classAttributeIconSize 0
skinparam shadowing false
skinparam linetype ortho
skinparam dpi 300
skinparam defaultFontSize 12
skinparam classFontSize 12
skinparam classAttributeFontSize 10
skinparam packageFontSize 13

hide empty members

package "core" {
    class SignatureLoader <<singleton>>
}

package "detectors" {
    abstract class BaseDetector <<abstract>>
    class DetectorFactory <<factory>>
}

package "services" {
    abstract class BaseServices <<abstract>>
}

class Analyzer <<facade>> {
    +analyze(url, depth_data)
    +analyze_snapshot(snapshot_url)
}

Analyzer --> DetectorFactory
Analyzer --> BaseServices
Analyzer --> SignatureLoader
DetectorFactory ..> BaseDetector

@enduml
```

## 2. Analyzer Orchestration

```plantuml
@startuml
title Analyzer Orchestration

top to bottom direction

skinparam backgroundColor white
skinparam packageStyle rectangle
skinparam classAttributeIconSize 0
skinparam shadowing false
skinparam linetype ortho
skinparam dpi 300
skinparam defaultFontSize 12
skinparam classFontSize 12
skinparam classAttributeFontSize 10
skinparam packageFontSize 13

hide empty members

class Analyzer <<facade>> {
    -TIMEOUT: int
    -DEFAULT_HEADERS: dict
    -factory: DetectorFactory
    -dns: DnsRecordService
    -geo: GeoService
    -whois: WhoisService
    -wayback: WaybackService
    -probe_paths: list
    +analyze(url: str, depth_data: bool): dict
    +analyze_snapshot(snapshot_url: str): dict
    -_run_detectors(...)
    -_probe_paths_request(...)
    -_extract_resources(...)
    -_collect_probe_paths()
    -_normalize_url(...)
    -_fetch_page(...)
    -_extract_scripts(...)
}

class DetectorFactory <<factory>> {
    +create_all()
}

class SignatureLoader <<singleton>> {
    +get_all()
}

package "services" {
    class DnsRecordService <<service>>
    class GeoService <<service>>
    class WhoisService <<service>>
    class WaybackService <<service>>
}

Analyzer o-- DetectorFactory
Analyzer o-- DnsRecordService
Analyzer o-- GeoService
Analyzer o-- WhoisService
Analyzer o-- WaybackService
Analyzer ..> SignatureLoader

@enduml
```

## 3. Detectors Hierarchy

```plantuml
@startuml
title Detectors Hierarchy

top to bottom direction

skinparam backgroundColor white
skinparam packageStyle rectangle
skinparam classAttributeIconSize 0
skinparam shadowing false
skinparam linetype ortho
skinparam dpi 300
skinparam defaultFontSize 12
skinparam classFontSize 12
skinparam classAttributeFontSize 10
skinparam packageFontSize 13

hide empty members

abstract class BaseDetector <<abstract>> {
    #signatures: dict
    +__init__(signatures: dict)
    +{abstract} detect(...)
    #_match_header(pattern: str, headers: dict)
    #_score_to_confidence(score: int)
    #_build_result(...)
}

class FrontendDetector <<detector>> {
    +detect(...)
}

class BackendDetector <<detector>> {
    +detect(...)
}

class CDNDetector <<detector>> {
    +detect(...)
}

FrontendDetector --|> BaseDetector
BackendDetector --|> BaseDetector
CDNDetector --|> BaseDetector

@enduml
```

## 4. Services Hierarchy

```plantuml
@startuml
title Services Hierarchy

top to bottom direction

skinparam backgroundColor white
skinparam packageStyle rectangle
skinparam classAttributeIconSize 0
skinparam shadowing false
skinparam linetype ortho
skinparam dpi 300
skinparam defaultFontSize 12
skinparam classFontSize 12
skinparam classAttributeFontSize 10
skinparam packageFontSize 13

hide empty members

abstract class BaseServices <<abstract>> {
    +{abstract} fetch_service(url: str, depth_data: bool)
}

class DnsRecordService <<service>> {
    +fetch_service(url, depth_data)
    +get_dns_records(url)
}

class GeoService <<service>> {
    -api_endpoint: str
    +fetch_service(url, depth_data)
    +get_geoinfo(url, all_data)
}

class WhoisService <<service>> {
    +fetch_service(url, depth_data)
}

class WaybackService <<service>> {
    +fetch_service(url, depth_data)
}

DnsRecordService --|> BaseServices
GeoService --|> BaseServices
WhoisService --|> BaseServices
WaybackService --|> BaseServices

@enduml
```

## 5. Core Components

```plantuml
@startuml
title Core Components

top to bottom direction

skinparam backgroundColor white
skinparam packageStyle rectangle
skinparam classAttributeIconSize 0
skinparam shadowing false
skinparam linetype ortho
skinparam dpi 300
skinparam defaultFontSize 12
skinparam classFontSize 12
skinparam classAttributeFontSize 10
skinparam packageFontSize 13

hide empty members

class SignatureLoader <<singleton>> {
    -_instance
    -_signatures: dict
    +__new__()
    -_load()
    +get(category: str): dict
    +get_all(): dict
}

class DetectorFactory <<factory>> {
    -_registry: dict
    -_loader: SignatureLoader
    +__init__()
    +create(category: str): BaseDetector
    +create_all(): dict
    +{static} register(category: str, detector_class: type)
}

DetectorFactory o-- SignatureLoader

@enduml
```

## 6. Modules / Utility Functions

```plantuml
@startuml
title Modules & Utility Functions

top to bottom direction

skinparam backgroundColor white
skinparam packageStyle rectangle
skinparam classAttributeIconSize 0
skinparam shadowing false
skinparam linetype ortho
skinparam dpi 300
skinparam defaultFontSize 12
skinparam classFontSize 12
skinparam classAttributeFontSize 10
skinparam packageFontSize 13

hide empty members

class "js_fetcher" <<module>> {
    -MAX_JS_SIZE: int
    -MAX_JS_FILES: int
    -TIMEOUT: int
    -DEFAULT_HEADERS: dict
    -PRIORITY_KEYWORDS: list
    -SKIP_KEYWORDS: list
    +fetch_js_contents(base_url, script_srcs)
    -_prioritize(srcs)
    -_is_same_origin_hint(url)
    -_download(src, base_url)
}

class Analyzer <<facade>>

Analyzer ..> "js_fetcher"

@enduml
```

## 7. Complete Class Diagram - Simplified Methods

```plantuml
@startuml
title Complete Class Diagram - Simplified Methods

skinparam backgroundColor white
skinparam packageStyle rectangle
skinparam classAttributeIconSize 0
skinparam shadowing false
skinparam linetype ortho
skinparam dpi 300
skinparam defaultFontSize 12
skinparam classFontSize 12
skinparam classAttributeFontSize 10
skinparam packageFontSize 13

hide empty members

package "core" {
    class SignatureLoader <<singleton>> {
        -_instance
        -_signatures
        +get()
        +get_all()
        -_load()
    }
    
    class "js_fetcher" <<module>> {
        -MAX_JS_SIZE
        -MAX_JS_FILES
        +fetch_js_contents()
        -_prioritize()
        -_is_same_origin_hint()
        -_download()
    }
}

package "detectors" {
    abstract class BaseDetector <<abstract>> {
        #signatures
        +detect()
        #_match_header()
        #_score_to_confidence()
        #_build_result()
    }
    class FrontendDetector <<detector>> {
        +detect()
    }
    class BackendDetector <<detector>> {
        +detect()
    }
    class CDNDetector <<detector>> {
        +detect()
    }
    class DetectorFactory <<factory>> {
        -_registry
        -_loader
        +create()
        +create_all()
        +{static} register()
    }
    
    FrontendDetector --|> BaseDetector
    BackendDetector --|> BaseDetector
    CDNDetector --|> BaseDetector
}

package "services" {
    abstract class BaseServices <<abstract>> {
        +fetch_service()
    }
    class DnsRecordService <<service>> {
        +fetch_service()
        +get_dns_records()
    }
    class GeoService <<service>> {
        -api_endpoint
        +fetch_service()
        +get_geoinfo()
    }
    class WhoisService <<service>> {
        +fetch_service()
    }
    class WaybackService <<service>> {
        +fetch_service()
    }

    DnsRecordService --|> BaseServices
    GeoService --|> BaseServices
    WhoisService --|> BaseServices
    WaybackService --|> BaseServices
}

class Analyzer <<facade>> {
    -TIMEOUT
    -DEFAULT_HEADERS
    +analyze()
    +analyze_snapshot()
    -_run_detectors()
    -_probe_paths_request()
    -_extract_resources()
    -_collect_probe_paths()
    -_normalize_url()
    -_fetch_page()
    -_extract_scripts()
}

Analyzer o-- DetectorFactory
Analyzer o-- DnsRecordService
Analyzer o-- GeoService
Analyzer o-- WhoisService
Analyzer o-- WaybackService
Analyzer ..> SignatureLoader
Analyzer ..> "js_fetcher"

DetectorFactory o-- SignatureLoader
DetectorFactory ..> BaseDetector

@enduml
```

## 8. Coverage Matrix

| Clase / Módulo | Diagrama donde aparece | Rol | Relaciones principales |
| --- | --- | --- | --- |
| `Analyzer` | General Class Overview, Analyzer Orchestration, Modules | Orquestador / Facade principal | `DetectorFactory`, `BaseServices`, `js_fetcher` |
| `DetectorFactory` | General Class Overview, Analyzer Orchestration, Core Components | Factory para instanciar detectores | `BaseDetector`, `SignatureLoader` |
| `BaseDetector` | General Class Overview, Detectors Hierarchy | Interfaz base para detectores | `FrontendDetector`, `BackendDetector`, `CDNDetector` |
| `FrontendDetector` | Detectors Hierarchy | Detector de tecnologías Frontend | Hereda de `BaseDetector` |
| `BackendDetector` | Detectors Hierarchy | Detector de tecnologías Backend | Hereda de `BaseDetector` |
| `CDNDetector` | Detectors Hierarchy | Detector de infraestructura y CDN | Hereda de `BaseDetector` |
| `BaseServices` | General Class Overview, Services Hierarchy | Interfaz base para servicios | `DnsRecordService`, `GeoService`, `WhoisService`, `WaybackService` |
| `DnsRecordService` | Analyzer Orchestration, Services Hierarchy | Servicio para consultas DNS | Hereda de `BaseServices`, usado por `Analyzer` |
| `GeoService` | Analyzer Orchestration, Services Hierarchy | Servicio para geolocalización | Hereda de `BaseServices`, usado por `Analyzer` |
| `WhoisService` | Analyzer Orchestration, Services Hierarchy | Servicio para obtener información WHOIS | Hereda de `BaseServices`, usado por `Analyzer` |
| `WaybackService` | Analyzer Orchestration, Services Hierarchy | Servicio de consulta a Wayback Machine | Hereda de `BaseServices`, usado por `Analyzer` |
| `SignatureLoader` | General Class Overview, Analyzer Orchestration, Core Components | Singleton que carga `signatures.json` | `DetectorFactory`, `Analyzer` |
| `js_fetcher` | Modules / Utility Functions | Funciones para descarga de archivos JS | Usado por `Analyzer` |

## 9. Notes for Presentation
Durante una exposición o revisión técnica, puedes usar estos puntos para explicar y defender el diseño de los diagramas:

*   **General Class Overview:** Muestra la visión a "vuelo de pájaro" de todo el proyecto. Presenta los tres grandes paquetes (core, detectors, services) interactuando con el orquestador principal (`Analyzer`). Sirve como introducción.
*   **Analyzer Orchestration:** Explica cómo la clase principal inicializa y administra todos sus recursos. Destaca la composición y agregación que tiene `Analyzer` con todos los servicios particulares y el `DetectorFactory`.
*   **Detectors Hierarchy:** Demuestra el uso claro del Patrón Strategy / Polimorfismo. Todos los detectores implementan la misma base abstracta `BaseDetector`, lo que permite que el `DetectorFactory` y el `Analyzer` los manipulen de forma estandarizada e independiente de su tipo.
*   **Services Hierarchy:** Al igual que en detectores, evidencia el uso de polimorfismo. Todos los servicios garantizan la existencia del método `fetch_service()`.
*   **Core Components:** Destaca la aplicación del patrón Singleton en `SignatureLoader` para optimizar la carga de reglas y cómo se vincula íntimamente con `DetectorFactory`.
*   **Diseño Modular:** Dividir los diagramas ha permitido demostrar que el software sigue principios SOLID. Las interfaces están separadas, y la división en diferentes vistas previene la saturación cognitiva para los lectores. Todo fluye de manera lógica de arriba a abajo, lo que es óptimo para los formatos de documentos verticales.
