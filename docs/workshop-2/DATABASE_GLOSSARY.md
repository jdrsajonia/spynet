# Database Glossary

Technical terminology used in the SpyNet persistence layer.

| Term | Meaning in SpyNet |
|---|---|
| ORM | Layer that maps Django model objects to SQL operations |
| Model | Python class representing a database table |
| Migration | Versioned description of a schema change |
| Foreign key | Reference from a child row to its parent |
| One-to-one | Relationship allowing at most one related result |
| Cascade | Automatic deletion of dependent rows |
| Transaction | Group of operations committed or rolled back together |
| Atomicity | Guarantee that a transaction completes fully or not at all |
| Constraint | Rule enforced by PostgreSQL |
| XOR | Rule requiring exactly one of two possible parents |
| JSONField | PostgreSQL-backed field for semistructured data |
| QuerySet | Lazy representation of a Django database query |
| `bulk_create` | Efficient insertion of multiple rows |
| Normalization | Separation of repeated data into related tables |
| Rollback | Reversal of a failed transaction |
| Primary key | Unique identifier for a row |
| Index | Structure that accelerates selected database queries |
| Volume | Docker storage that persists PostgreSQL data |

