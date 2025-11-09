#!/bin/bash
set -euo pipefail

poetry run alembic upgrade head
exec poetry run uvicorn core.app:app --host ${CORE_HOST:-0.0.0.0} --port ${CORE_PORT:-8000}
