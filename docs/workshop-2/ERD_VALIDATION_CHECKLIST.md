# ER Diagram Validation Checklist

Use this checklist whenever the SpyNet relational model changes.

## Entities

- [ ] All Django models appear in the ER diagram.
- [ ] Primary keys are identified.
- [ ] Foreign keys point to the correct parent.
- [ ] Optional fields are marked as nullable.
- [ ] Field names match `api/models.py`.
- [ ] New model fields are represented.

## Relationships

- [ ] Domain has multiple analyses.
- [ ] Analysis has optional WHOIS, Geo, DNS and Wayback results.
- [ ] DnsResult contains multiple DnsRecord rows.
- [ ] WaybackResult contains multiple snapshots.
- [ ] Technology belongs to Analysis or WaybackSnapshot.
- [ ] AnalysisError and AnalysisTag belong to Analysis.

## Integrity

- [ ] `Domain.name` remains unique.
- [ ] Cascade deletion is represented.
- [ ] The Technology XOR constraint is documented.
- [ ] No relationship line crosses an entity.
- [ ] Cardinalities are readable and unambiguous.

## Synchronization

- [ ] Run `python manage.py makemigrations --check`.
- [ ] Compare the ER diagram with `api/models.py`.
- [ ] Update the technical database guide after schema changes.
- [ ] Update API documentation if response fields change.

