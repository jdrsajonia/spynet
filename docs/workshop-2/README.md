# Workshop 2 - Diseno y arquitectura de SpyNet

Este directorio reune los artefactos de diseno, arquitectura y persistencia desarrollados para el segundo workshop.

## Documentos

| Recurso | Descripcion |
|---|---|
| [Workshop 2](./spynet_workshop_2.pdf) | Documento principal de diseno y arquitectura |
| [Diagrama entidad-relacion](./Spynet_ER_Diagram.pdf) | Modelo relacional actualizado |
| [Guia tecnica de base de datos](./DATABASE_TECHNICAL_GUIDE.md) | PostgreSQL, Django ORM, migraciones y persistencia |

## Componentes relacionados

- `api/models.py`: entidades, relaciones y restricciones.
- `api/persistence.py`: persistencia normalizada y transacciones.
- `api/migrations/`: evolucion versionada del esquema.
- `config/settings.py`: conexion con PostgreSQL.
- `docker-compose.yml`: contenedor, healthcheck y volumen de datos.

## Decisiones principales

1. PostgreSQL se utiliza como motor relacional.
2. Domain agrupa multiples ejecuciones de Analysis.
3. Los registros DNS se almacenan de forma normalizada.
4. Technology pertenece a un Analysis o a un WaybackSnapshot.
5. La restriccion XOR evita tecnologias huerfanas o con doble padre.
6. Las escrituras principales utilizan transacciones atomicas.
7. Los fallos parciales se registran mediante AnalysisError.

## Navegacion

- [README principal](../../README.md)
- [Documentacion actualizada del Workshop 1](../workshop-1/README_UPDATE.md)
