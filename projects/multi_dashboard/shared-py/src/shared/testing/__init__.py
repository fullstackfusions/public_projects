"""pytest fixtures shared across backend services.

Importing ``shared.testing`` adds nothing to the runtime — fixtures are
declared as functions you opt into by importing them in your ``conftest.py``::

    # backends/scheduler-py/app/tests/conftest.py
    from shared.testing.fastapi import async_client  # noqa: F401
    from shared.testing.sql import sqlite_engine, db_session  # noqa: F401
    from shared.testing.jwt import auth_headers  # noqa: F401
"""
