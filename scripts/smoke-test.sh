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

# Test credentials (create a test user if needed, or use existing)
TEST_USER="${SMOKE_TEST_USER:-smoketest}"
TEST_PASS="${SMOKE_TEST_PASS:-smoketest123}"
TEST_EMAIL="${SMOKE_TEST_EMAIL:-smoketest@example.com}"

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

check_json_key() {
    local name="$1" body="$2" key="$3"
    if echo "$body" | grep -q "\"$key\":"; then
        echo "PASS  $name has key '$key'"
    else
        echo "FAIL  $name missing key '$key'"
        fail=1
    fi
}

check_array_length() {
    local name="$1" body="$2" key="$3" min_len="$4"
    # Use python to parse JSON and check array length
    len=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('$key', [])))" 2>/dev/null || echo 0)
    if [ "$len" -ge "$min_len" ]; then
        echo "PASS  $name '$key' length=$len (>= $min_len)"
    else
        echo "FAIL  $name '$key' length=$len (expected >= $min_len)"
        fail=1
    fi
}

authenticate() {
    echo "== Authenticating test user =="
    # Try login first
    local login_resp
    login_resp=$(curl -s -m 30 -X POST "$BACKEND/api/v1/token/" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$TEST_USER\",\"password\":\"$TEST_PASS\"}")

    if echo "$login_resp" | grep -q '"access"'; then
        ACCESS_TOKEN=$(echo "$login_resp" | python3 -c "import sys, json; print(json.load(sys.stdin)['access'])" 2>/dev/null)
        echo "PASS  login successful"
        return 0
    fi

    # If login fails, try register
    echo "  login failed, attempting registration..."
    local reg_resp
    reg_resp=$(curl -s -m 30 -X POST "$BACKEND/api/v1/register/" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$TEST_USER\",\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\"}")

    if echo "$reg_resp" | grep -q '"username"'; then
        # Registration successful, now login
        login_resp=$(curl -s -m 30 -X POST "$BACKEND/api/v1/token/" \
            -H "Content-Type: application/json" \
            -d "{\"username\":\"$TEST_USER\",\"password\":\"$TEST_PASS\"}")
        if echo "$login_resp" | grep -q '"access"'; then
            ACCESS_TOKEN=$(echo "$login_resp" | python3 -c "import sys, json; print(json.load(sys.stdin)['access'])" 2>/dev/null)
            echo "PASS  registration + login successful"
            return 0
        fi
    fi

    echo "FAIL  authentication failed: $login_resp"
    fail=1
    return 1
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
    authenticate || exit 1

    echo "== Predict (slow, ~40s) =="
    body=$(curl -s -m 300 -X POST "$BACKEND/api/v1/predict/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -d '{"ticker":"AAPL"}')
    if echo "$body" | grep -q '"status":"success"'; then
        echo "PASS  predict returned success"
        # Validate new response structure with data arrays
        check_json_key "predict" "$body" "historical_prices"
        check_json_key "predict" "$body" "historical_dates"
        check_json_key "predict" "$body" "ma100"
        check_json_key "predict" "$body" "ma200"
        check_json_key "predict" "$body" "y_test"
        check_json_key "predict" "$body" "y_predicted"
        check_json_key "predict" "$body" "test_indices"
        check_json_key "predict" "$body" "mse"
        check_json_key "predict" "$body" "rmse"
        check_json_key "predict" "$body" "r2"
        # Check array lengths are reasonable (at least some data points)
        check_array_length "predict" "$body" "historical_prices" 100
        check_array_length "predict" "$body" "y_test" 10
        check_array_length "predict" "$body" "y_predicted" 10
        # Ensure old image URL keys are NOT present (backward compatibility check)
        if echo "$body" | grep -q '"plot_img"'; then
            echo "FAIL  predict still returns old 'plot_img' key"
            fail=1
        else
            echo "PASS  predict no longer returns legacy image URL keys"
        fi
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