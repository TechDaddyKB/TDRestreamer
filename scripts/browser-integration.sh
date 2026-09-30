#!/usr/bin/env bash
set -euo pipefail
set -a
source .env
set +a
export DATABASE_URL="postgres://tdr_app:${TDR_DB_PASSWORD}@127.0.0.1:55432/tdr_test?sslmode=disable"
export TDR_LISTEN=127.0.0.1:18080
export TDR_E2E_URL=http://127.0.0.1:18080
export TDR_E2E_FIXTURE=true
mkdir -p runtime
./bin/control > runtime/browser-control.log 2>&1 &
control_pid=$!
trap 'kill "$control_pid" 2>/dev/null || true; wait "$control_pid" 2>/dev/null || true' EXIT
for attempt in $(seq 1 50); do
  if ! kill -0 "$control_pid" 2>/dev/null; then echo 'Control failed to start; see runtime/browser-control.log'; exit 1; fi
  if curl -fsS "$TDR_E2E_URL/readyz" >/dev/null; then break; fi
  sleep 0.2
done
(cd web && npm run test:e2e)
