# SANDSTONE v2.1 — Deployment Reconciliation Guide
## For Jemell Sanders — Prescriptive Deployment Instructions

**Date:** March 13, 2026
**From:** Oliver / Claude architecture review
**Scope:** Reconcile currently deployed code (d3ipudxbc9u53q.cloudfront.net) with v2.1 final package

---

## EXECUTIVE SUMMARY

The currently deployed codebase has 14 files that need updating. 2 files need deleting. 4 new files need adding. 1 database migration needs running. 1 frontend change is required.

**The v2.1 package (`sandstone-v2.1-final.zip`) is a complete drop-in replacement for the entire Python backend.** Do not cherry-pick files — replace the whole backend directory.

---

## FILE-BY-FILE CHANGELOG: DEPLOYED → v2.1

### CRITICAL CHANGES (will break things if missed)

| File | Status | What Changed |
|------|--------|-------------|
| `config.py` | **REWRITTEN** | Removed `DATABASE_PATH`, `USE_POSTGRES` (always PG now). Removed `TDS_DELTA`, `TDS_WEIGHTS`. Added `LDS_EPSILON=0.15`, `LDS_WEIGHTS`, `INJECTION_THRESHOLD=0.25`, `PDV_THRESHOLD=3`, `PDV_BOOST_DELTA=0.10`, `RESIDUAL_FLOOR_FRACTION=0.10`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`. Changed `DEFAULT_WEIGHTS` from `[0.2,0.2,0.2,0.2,0.2]` to `[0.20,0.30,0.20,0.15,0.15]`. |
| `api/routes.py` | **REWRITTEN** | Added identity extraction (names/partners/locations persist across sessions). Rewrote system prompt (removed therapist framing, banned asterisk emotes). Added admin password protection (`@admin_required` decorator + `/admin/login` endpoint). Added prior-session summary injection. Renamed all TDS→LDS, AAHS→LCS variables. |
| `core/tds.py` | **DELETE** | Replaced by `core/lds.py`. |
| `core/lds.py` | **NEW** | Renamed from tds.py. All functions renamed: `calculate_tds`→`calculate_lds`, `calculate_ncs`→`calculate_csd`, `calculate_acd`→`calculate_icd`, `calculate_ccm`→`calculate_ccs`, `calculate_ssi`→`calculate_vsi`. **CRITICAL FIX: LDS correction is now ADDITIVE** (`salience + ε × LDS`) not subtractive (`salience × (1 - δ × TDS)`). Old formula reduced salience when divergence was detected — the opposite of intended behavior. |
| `core/scoring.py` | **MODIFIED** | `calculate_aahs()` renamed to `calculate_lcs()`. All internal variables `aahs` → `lcs`. Return dict key `'aahs'` → `'lcs'`. `calculate_base_score()` parameter renamed. |
| `core/ingestion.py` | **MODIFIED** | Import changed: `from core.tds` → `from core.lds`. Function calls renamed: `calculate_tds` → `calculate_lds`, `update_tds_score` → `update_lds_score`. Variable `tds` → `lds`. Scores dict key `'aahs'` → `'lcs'`. |
| `core/decay.py` | **MODIFIED** | Import changed: `from core.tds import apply_tds_correction` → `from core.lds import apply_lds_correction`. Field reference: `node.get('tds_score')` → `node.get('lds_score')`. |
| `core/retrieval.py` | **MODIFIED** | Field reference: `'tds_score': n['tds_score']` → `'lds_score': n['lds_score']`. |
| `db/database.py` | **MODIFIED** | All SQL field references: `aahs` → `lcs`, `tds_score` → `lds_score`. Function `update_tds_score()` → `update_lds_score()`. Removed SQLite code path — PostgreSQL only. Uses `psycopg2` with `RealDictCursor`. `_hash_password()` uses bcrypt. Added `_verify_password()`. |
| `db/schema.sql` | **MODIFIED** | Column `aahs` → `lcs`. Column `tds_score` → `lds_score`. Added `UNIQUE` on `study_participants.email`. Added index `idx_participants_email`. Uses `DOUBLE PRECISION` (not `REAL`). Uses `BOOLEAN DEFAULT FALSE` (not `BOOLEAN DEFAULT 0`). |
| `requirements.txt` | **MODIFIED** | Added `bcrypt>=4.1.0` and `testing.postgresql>=1.3.0`. |

### UNCHANGED FILES (verify present, no action needed)

| File | Status |
|------|--------|
| `app.py` | Unchanged from Phase 2 build |
| `core/bedrock.py` | Unchanged |
| `appspec.yml` | Unchanged |
| `buildspec-backend.yml` | Unchanged |
| `buildspec-frontend.yml` | Unchanged |
| `DEPLOYMENT.md` | Unchanged |
| `run_tests.sh` | Unchanged |
| `infra/lambda_decay/lambda_handler.py` | Unchanged |
| `infra/lambda_decay/requirements.txt` | Unchanged |
| `scripts/*` (deployment scripts) | Unchanged |

### NEW FILES

| File | Purpose |
|------|---------|
| `core/lds.py` | Linguistic Divergence Score (replaces tds.py) |
| `tests/test_lds.py` | Tests for LDS (replaces test_tds.py) |
| `tests/conftest.py` | Shared PostgreSQL test setup base class |
| `CHANGELOG_v2_1.md` | Full change log with patent alignment matrix |
| `MVP_FIXES.md` | Frontend guidance for rating bar and admin login |

### FILES TO DELETE

| File | Reason |
|------|--------|
| `core/tds.py` | Replaced by `core/lds.py` |
| `tests/test_tds.py` | Replaced by `tests/test_lds.py` |

---

## STEP-BY-STEP DEPLOYMENT PROCEDURE

### Pre-Deployment: Database Migration (MUST DO FIRST)

The column renames must happen before the new code deploys, or the app will crash on startup.

**SSH into the EC2 instance:**
```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

**Connect to RDS and run the migration:**
```bash
# Get the RDS endpoint from CloudFormation outputs or .env
source /opt/sandstone/.env

# Connect to PostgreSQL
psql -h sandstone-db-production.c2l5ggnslsuq.us-east-1.rds.amazonaws.com -U sandstone_admin -d sandstone

DB_PASSWORD=SandstoneDB2026!

# Run these two ALTER TABLE commands:
ALTER TABLE memory_nodes RENAME COLUMN aahs TO lcs;
ALTER TABLE memory_nodes RENAME COLUMN tds_score TO lds_score;

# Verify:
\d memory_nodes
# Should show 'lcs' and 'lds_score' columns, NOT 'aahs' or 'tds_score'

# Exit psql:
\q
```

If the database has no data yet (fresh deployment), you can skip the ALTER TABLE and just let the new schema.sql create the tables with the correct column names.

---

### Step 1: Backup Current Deployment

```bash
ssh ubuntu@YOUR_EC2_IP
cd /opt/sandstone
sudo cp -r . /opt/sandstone-backup-$(date +%Y%m%d)
echo "Backup created"
```

---

### Step 2: Upload v2.1 Package

**From your local machine:**
```bash
# Unzip the package locally first
unzip sandstone-v2.1-final.zip -d sandstone-v2.1

# SCP the files to EC2
scp -i your-key.pem -r sandstone-v2.1/* ubuntu@YOUR_EC2_IP:/tmp/sandstone-v2.1/
```

---

### Step 3: Replace Backend Files

**On the EC2 instance:**
```bash
cd /opt/sandstone

# Delete the old tds.py (CRITICAL — imports will fail if both exist)
sudo rm -f core/tds.py
sudo rm -f tests/test_tds.py

# Copy all v2.1 files over the existing deployment
sudo cp /tmp/sandstone-v2.1/config.py .
sudo cp /tmp/sandstone-v2.1/api/routes.py api/
sudo cp /tmp/sandstone-v2.1/core/lds.py core/
sudo cp /tmp/sandstone-v2.1/core/scoring.py core/
sudo cp /tmp/sandstone-v2.1/core/ingestion.py core/
sudo cp /tmp/sandstone-v2.1/core/decay.py core/
sudo cp /tmp/sandstone-v2.1/core/retrieval.py core/
sudo cp /tmp/sandstone-v2.1/db/database.py db/
sudo cp /tmp/sandstone-v2.1/db/schema.sql db/
sudo cp /tmp/sandstone-v2.1/requirements.txt .
sudo cp /tmp/sandstone-v2.1/tests/*.py tests/
sudo cp /tmp/sandstone-v2.1/CHANGELOG_v2_1.md .
sudo cp /tmp/sandstone-v2.1/MVP_FIXES.md .

# Verify tds.py is gone
ls core/tds.py 2>/dev/null && echo "ERROR: tds.py still exists!" || echo "OK: tds.py removed"

# Verify lds.py is present
ls core/lds.py && echo "OK: lds.py present" || echo "ERROR: lds.py missing!"
```

---

### Step 4: Install New Dependencies

```bash
cd /opt/sandstone
source venv/bin/activate   # or wherever your virtualenv is
pip install bcrypt>=4.1.0
pip install -r requirements.txt
```

---

### Step 5: Update .env File

Add these new environment variables to `/opt/sandstone/.env`:

```bash
# Add to .env (these have sensible defaults in config.py but can be overridden)
INJECTION_THRESHOLD=0.25
PDV_THRESHOLD=3
PDV_BOOST_DELTA=0.10
ADMIN_USERNAME=Sandstone-Admin
ADMIN_PASSWORD=Iamgeekn!
```

**Remove these deprecated variables if present:**
```bash
# Remove from .env (no longer used):
# DATABASE_PATH=...     (removed — always PostgreSQL)
# USE_POSTGRES=true     (removed — always PostgreSQL)
```

---

### Step 6: Restart the Application

```bash
# Restart gunicorn
sudo systemctl restart sandstone

# Or if using supervisord:
sudo supervisorctl restart sandstone

# Or if running directly:
sudo pkill -f gunicorn
cd /opt/sandstone
source venv/bin/activate
gunicorn app:app -b 0.0.0.0:5000 -w 4 --timeout 120 &
```

---

### Step 7: Verify Deployment

```bash
# Health check
curl http://localhost:5000/health
# Expected: {"status":"ok","timestamp":"..."}

# Test admin protection (should fail without credentials)
curl http://localhost:5000/admin/stats
# Expected: {"error":"Admin authentication required"}

# Test admin login
curl -X POST http://localhost:5000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"Sandstone-Admin","password":"Iamgeekn!"}'
# Expected: {"status":"authenticated","admin_token":"..."}

# Test admin with token
TOKEN=$(curl -s -X POST http://localhost:5000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"Sandstone-Admin","password":"Iamgeekn!"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['admin_token'])")

curl http://localhost:5000/admin/stats -H "X-Admin-Token: $TOKEN"
# Expected: {"total_participants":...,"total_ratings":...}

# Via CloudFront (test the full path)
curl https://d3ipudxbc9u53q.cloudfront.net/api/health
# Expected: {"status":"ok","timestamp":"..."}
```

---

### Step 8: Test Core Functionality

```bash
# 1. Sign up a test user
curl -X POST https://d3ipudxbc9u53q.cloudfront.net/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"deploy-test@sandstone.test","password":"test123","display_name":"Deploy Test"}'

# 2. Get the token from response, then test chat/split
# (replace TOKEN with actual token from signup response)
curl -X POST https://d3ipudxbc9u53q.cloudfront.net/api/chat/split \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"message":"Hello, my name is Oliver and I am feeling anxious and overwhelmed about work"}'

# 3. Check memory was created (should have identity + emotional nodes)
# Get user_id from signup response
curl https://d3ipudxbc9u53q.cloudfront.net/api/memory/USER_ID \
  -H "Authorization: Bearer TOKEN"
# Expected: nodes with topic 'identity_user_name' AND emotional topics
```

---

## FRONTEND CHANGES REQUIRED

Two frontend changes that Jemell needs to make in the React code:

### 1. Rating Bar: Move from Modal to Fixed Position

The rating sliders currently pop up as a modal overlay after each LLM response, covering the conversation. Move them to a permanently visible strip below the message input.

**Current (broken):**
```
[Conversation A & B panels]
  [MODAL OVERLAY - rating sliders - blocks view]
[Message input]
```

**Target (fixed):**
```
[Conversation A & B panels - never blocked]
[Message input] [Send]
[Rating section - always visible below input]
  Rate A: [Attune] [Accuracy] [Natural]
  Rate B: [Attune] [Accuracy] [Natural]
  Preference: [A] [B] [Tie]  [Submit]
```

Key changes:
- Remove the modal/dialog wrapper around rating component
- Remove `position: fixed/absolute` and backdrop overlay
- Place rating JSX below the message input in the flex layout
- Make it `position: relative`, not `fixed`
- Remove the dismiss/minimize button — it's always visible now
- Only show after first exchange (when there's something to rate)
- Ratings are optional — user can send new messages without submitting

See `MVP_FIXES.md` section 3 for full React component code.

### 2. Admin Tab: Add Login Gate

The admin tab now requires separate credentials. The frontend needs:

```javascript
// Before showing admin content, call:
const res = await fetch('/api/admin/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'Sandstone-Admin',
    password: 'Iamgeekn!'
  })
});
const { admin_token } = await res.json();

// Store token
sessionStorage.setItem('adminToken', admin_token);

// All admin API calls must include:
headers: { 'X-Admin-Token': sessionStorage.getItem('adminToken') }
```

Show a username/password form when the admin tab is clicked. Only load admin data after successful authentication.

### 3. Frontend Variable References

If the frontend JavaScript parses API response fields, update:
- `tds_score` → `lds_score`
- `aahs` → `lcs`

These appear in memory state responses from `/admin/user/{id}/memory`.

---

## ROLLBACK PROCEDURE

If something breaks:

```bash
ssh ubuntu@YOUR_EC2_IP

# Restore backup
sudo rm -rf /opt/sandstone
sudo mv /opt/sandstone-backup-YYYYMMDD /opt/sandstone

# Reverse the database migration
psql -h $DB_HOST -U $DB_USER -d $DB_NAME
ALTER TABLE memory_nodes RENAME COLUMN lcs TO aahs;
ALTER TABLE memory_nodes RENAME COLUMN lds_score TO tds_score;
\q

# Restart
sudo systemctl restart sandstone
```

---

## POST-DEPLOYMENT CHECKLIST

- [ ] Database migration ran (aahs→lcs, tds_score→lds_score)
- [ ] `core/tds.py` deleted from server
- [ ] `core/lds.py` present on server
- [ ] `bcrypt` installed in virtualenv
- [ ] `.env` updated with new variables
- [ ] Gunicorn restarted
- [ ] `/health` returns 200
- [ ] `/admin/stats` returns 401 without token (admin protection working)
- [ ] `/admin/login` returns token with correct credentials
- [ ] Signup creates identity nodes (check `/memory/{user_id}` for `identity_user_name`)
- [ ] Chat responses do NOT contain asterisk emotes (`*warmly*` etc.)
- [ ] New session remembers user's name from prior session
- [ ] Frontend: rating bar below message input (not modal overlay)
- [ ] Frontend: admin tab behind login form
- [ ] CloudFront path (`/api/*`) routing verified end-to-end
