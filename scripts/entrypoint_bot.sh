#!/bin/bash
set -euo pipefail

exec poetry run python -m bot.main
