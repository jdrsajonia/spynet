# SpyNet Data Model Decisions

This document records the main design decisions behind the relational model in
`api/models.py`.

## Domain and Analysis are separate entities

`Domain` stores the unique domain name, while `Analysis` represents a concrete
execution over a URL. This supports multiple analyses of the same domain without
duplicating its identity.

## Service results use one-to-one relationships

WHOIS, Geo, DNS and Wayback produce at most one result block for each analysis.
Their rows can be absent when an external service fails.

## DNS records are normalized

`DnsResult` groups the DNS lookup and `DnsRecord` stores every record separately.
This makes record type, value and MX priority queryable.

## Technology has two optional parents

A technology can originate from a live `Analysis` or a historical
`WaybackSnapshot`. The `technology_exactly_one_parent` database constraint
requires exactly one of these foreign keys.

## JSON fields are limited to semistructured results

TLS, security and email-security results use `JSONField` because their internal
shape can evolve. Stable identities and relationships remain normalized.

## Cascading deletion prevents orphan rows

Foreign keys use `on_delete=models.CASCADE`. Deleting a parent removes its
dependent records and preserves referential integrity.

## Partial analyses remain observable

An unavailable external service does not invalidate every result. The analysis
can use the `partial` status and an `AnalysisError` row records the failure.

## Historical data keeps its origin

`WaybackResult` groups snapshots, and every `WaybackSnapshot` stores its timestamp
and archived URL. Historical technologies attach to the corresponding snapshot.

