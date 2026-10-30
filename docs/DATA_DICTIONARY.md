# Data dictionary

The field names and types are defined in `src/transport_ops/models.py`. All identifiers are immutable string primary keys; dates/times use ISO text in local synthetic service time. Coordinates are synthetic kilometres on a plane. Contact values are fictional (`.invalid` email and non-routable placeholders). Status values follow the PRD enums. Foreign-key fields encode the relationships documented in `SCHEMA.md`.
