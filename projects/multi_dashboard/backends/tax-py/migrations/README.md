# Migrations

No SQL migrations. Tax-backend uses MongoDB.

Index creation happens at startup in `app/lifespan.py` (idempotent).
Production index init lives in `infra/mongo/init/01-tax-indexes.js`.
