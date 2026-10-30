# Schema and relationships

The SQLite schema contains 14 tables. `AddressZone` is a parent of `Student` and `Stop`; `Student` owns guardian contacts and historical assignments; `Bus` and `Driver` serve dated routes; `Route` and `Stop` are joined by ordered `RouteStop` rows; assignments reference a route stop; attendance references assignment and date; notifications reference attendance and a guardian contact. Capacity changes, disruptions, and generic audit events preserve operational history.

All IDs are deterministic string primary keys. Foreign keys are enabled for every SQLite connection. Unique constraints protect route sequence/stop membership, one attendance row per assignment and date, and notification idempotency keys. Assignment effective-date overlap is checked in service and validation code.
