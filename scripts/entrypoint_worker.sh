#!/bin/bash
set -euo pipefail

exec poetry run python -m worker.scheduler
