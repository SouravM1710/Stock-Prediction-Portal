#!/usr/bin/env bash
# Smoke-test the live stock-prediction-portal deployments.
#
# Verifies the Vercel frontend (routes + SPA rewrites) and the Render backend
# (health + a real prediction). Run after any deploy to catch breakage early.
#
# Usage:
#   ./scripts/smoke-test.sh                # full check incl. slow predict (~40s)
#   SKIP_PREDICT=1 ./scripts/smoke-test.sh # skip the slow predict call
#
# Exit code 0 = all checks passed, 1 = at least one check failed.
set -u

FRONTEND="${FRONTEND_URL:-https://stock-prediction-portal-zeta.vercel.app}"
BACKEND="${BACKEND_URL:-https://stock-prediction-backend-i2sg.onrender.com}"

fail=0

check_http() {
    local name="$1" url="$2" expect="$3"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" -m 30 "$url" || echo 000)
    if [ "$code" = "$expect" ]; then
        echo "PASS  $name ($code)"
    else
        echo "FAIL  $name (expected $expect, got $code)"
        fail=1
    fi
}

echo "== Frontend ($FRONTEND) =="
check_http "root"              "$FRONTEND/" 200
check_http "deep link /register"  "$FRONTEND/register" 200
check_http "deep link /login"     "$FRONTEND/login" 200
check_http "deep link /dashboard" "$FRONTEND/dashboard" 200

if ! curl -s -m 30 "$FRONTEND/" | grep -q "Stock Prediction Portal"; then
    echo "FAIL  root page title missing"
    fail=1
else
    echo "PASS  root page title"
fi

echo "== Backend ($BACKEND) =="
check_http "health" "$BACKEND/api/v1/health/" 200

if ! curl -s -m 30 "$BACKEND/api/v1/health/" | grep -q '"status":"ok"'; then
    echo "FAIL  health body is not ok"
    fail=1
else
    echo "PASS  health body"
fi

if [ "${SKIP_PREDICT:-0}" != "1" ]; then
    echo "== Predict (slow, ~40s) =="
    body=$(curl -s -m 300 -X POST "$BACKEND/api/v1/predict/" \
        -H "Content-Type: application/json" -d '{"ticker":"AAPL"}')
    if echo "$body" | grep -q '"status":"success"'; then
        echo "PASS  predict returned success"
    else
        echo "FAIL  predict: $body"
        fail=1
    fi
else
    echo "== Predict: skipped (SKIP_PREDICT=1) =="
fi

if [ "$fail" -eq 0 ]; then
    echo "All checks passed."
else
    echo "Some checks failed."
fi
exit "$fail"
