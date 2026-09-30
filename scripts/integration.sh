#!/usr/bin/env bash
set -euo pipefail
set -a
source .env
set +a
export TDR_TEST_OWNER_URL="postgres://tdr_owner:${POSTGRES_PASSWORD}@127.0.0.1:55432/tdr_test?sslmode=disable"
export TDR_TEST_APP_URL="postgres://tdr_app:${TDR_DB_PASSWORD}@127.0.0.1:55432/tdr_test?sslmode=disable"
make integration
