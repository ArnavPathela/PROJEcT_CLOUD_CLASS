#!/usr/bin/env bash
# End-to-end check through the gateway: register -> login -> protected CRUD.
set -euo pipefail
BASE="${1:-http://localhost:8080}"
JSON='Content-Type: application/json'

echo "Waiting for gateway..."
for i in $(seq 1 30); do
  curl -fs "$BASE/health" >/dev/null 2>&1 && break
  sleep 2
done
curl -fs "$BASE/health"; echo

USER="ci$RANDOM"
curl -fs -X POST "$BASE/api/auth/register" -H "$JSON" \
  -d "{\"username\":\"$USER\",\"password\":\"secret123\"}" >/dev/null
TOKEN=$(curl -fs -X POST "$BASE/api/auth/login" -H "$JSON" \
  -d "{\"username\":\"$USER\",\"password\":\"secret123\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
echo "Logged in as $USER"

code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/students")
[ "$code" = "401" ] || { echo "Expected 401 without token, got $code"; exit 1; }
echo "Unauthenticated request correctly rejected"

curl -fs -X POST "$BASE/api/students" -H "$JSON" -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Smoke","email":"smoke@example.com","course":"CS"}' >/dev/null
curl -fs "$BASE/api/students" -H "Authorization: Bearer $TOKEN" | grep -q "Smoke"
echo "Smoke test passed"
