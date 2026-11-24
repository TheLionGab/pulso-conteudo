#!/usr/bin/env bash
set -euo pipefail
exec "${PULSO_PYTHON:-python3}" "$(dirname "$0")/integridade.py" obter "${1:?Informe a pasta public do trabalho}"
