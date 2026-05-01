"""Database access layer — schema definition and connection factory.

All SQLite writes go through ``orchestrator.event_logger``.
All SQLite reads  go through ``dashboard.queries``.
This package owns only the DDL and the raw connection.
"""
