#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

pytest \
    -m "not benchmark" \
    --cov dataconnect \
    --cov-report term \
    --cov-report html \
