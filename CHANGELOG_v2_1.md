# SANDSTONE CLOUD — v2.1 CHANGELOG
## Comprehensive Review & Alignment Pass
**Date:** March 10, 2026
**Scope:** Full codebase, patent documentation, test suite, deployment infrastructure

---

## CRITICAL FIXES

### C1: LDS Correction Direction (Code ↔ Patent Mismatch)
**Files:** `core/lds.py` (was `core/tds.py`)
**Severity:** Critical — code produced opposite behavior from patent claims

**Before:** `corrected = salience × (1 - δ × TDS)` → Higher TDS **reduced** salience
**After:** `corrected = salience + (ε × LDS)` → Higher LDS **increases** salience

**Why:** The patent correctly states that higher linguistic divergence means the user's language *understates* true significance. A user minimizing a topic should produce higher salience for that node (the system detects the understatement and compensates). The old code did the opposite — it penalized high-divergence nodes by reducing their salience, which would suppress exactly the nodes that should be surfaced.

**Parameter change:** `TDS_DELTA = 0.3` → `LDS_EPSILON = 0.15` (patent v2.1 aligned)

---

### C2: Variable Renames — Psychologically-Named → Computational Linguistics
**Files:** All `.py` files, `schema.sql`, `config.py`
**Severity:** Critical — patent prior art strategy depends on these renames

The patent v2.1 revision renamed all psychologically-framed variables to computational linguistics terminology. This shifts the prior art search space away from Picard's affective computing literature toward NLP/information retrieval. The codebase was still using the old names.

| Old Name | New Name | Old Desc | New Desc |
|----------|----------|----------|----------|
| AAHS (Affective-Alignment Heuristic Score) | LCS (Linguistic Consistency Score) | Measures stated emotional label alignment | Token co-occurrence between state-declaration and descriptor tokens |
| TDS (Truth Divergence Score) | LDS (Linguistic Divergence Score) | Gap between narrative and emotional truth | Multi-dimensional linguistic consistency composite |
| ACD (Affect-Content Divergence) | ICD (Intra-Message Consistency Detector) | Mismatch between emotion label and somatic markers | State-declaration / contradictory-context token co-occurrence |
| CCM (Cross-topic Contradiction Mapping) | CCS (Cross-Context Consistency Score) | Emotional pattern contradiction | Situation-descriptor / response-descriptor co-occurrence shift |
| NCS (Narrative Consistency Score) | CSD (Cross-Session Divergence) | Narrative contradiction signal | Cross-session semantic contradiction classifier |
| SSI (Somatic Signal Integration) | VSI (Valence Shift Index) | Rapid emotional tone shifts | Within-session sentiment polarity variance |

**Unchanged:** SDV, CSCV, SWV, PDV, B, λ, κ, S(t) — these were already neutral.

---

### C3: MVP Fixes Merged into Codebase
**Files:** `api/routes.py`
**Severity:** Critical — live deployment was running old routes.py

The pg-rewrite codebase (`sandstone-postgres.zip`) had the OLD routes.py without:
- Identity extraction (names, partners, locations not persisted across sessions)
- Corrected system prompt (old prompt caused *warmly* emotes)
- Admin password protection (any logged-in user could access /admin)
- Prior session summary (new sessions had no context continuity)

All four MVP fixes are now merged into the canonical routes.py.

---

### C4: B Composite Weights Updated to Patent Specification
**File:** `config.py`
**Severity:** Important — weights affect scoring behavior

**Before:** `DEFAULT_WEIGHTS = [0.2, 0.2, 0.2, 0.2, 0.2]` (equal)
**After:** `DEFAULT_WEIGHTS = [0.20, 0.30, 0.20, 0.15, 0.15]` (patent v2.1)

CSCV (cross-session consistency) gets the highest weight (0.30) because repeat cross-session return to a topic is the strongest behavioral signal of significance. PDV and SWV are downweighted (0.15 each) because they are noisier signals.

---

## IMPORTANT FIXES

### I1: Config Parameters Aligned to Patent v2.1
**File:** `config.py`

| Parameter | Old Value | New Value | Patent Spec |
|-----------|-----------|-----------|-------------|
| `DEFAULT_WEIGHTS` | `[0.2,0.2,0.2,0.2,0.2]` | `[0.20,0.30,0.20,0.15,0.15]` | §7.3.6 |
| `TDS_DELTA` | `0.3` | `LDS_EPSILON = 0.15` | §7.6.5 |
| `TDS_WEIGHTS` | `{ncs:0.35,acd:0.35,ccm:0.20,ssi:0.10}` | `LDS_WEIGHTS = {csd:0.35,icd:0.35,ccs:0.20,vsi:0.10}` | §7.6.5 |
| (new) | — | `INJECTION_THRESHOLD = 0.25` | §7.7 |
| (new) | — | `PDV_THRESHOLD = 3` | §7.5.2 |
| (new) | — | `PDV_BOOST_DELTA = 0.10` | §7.5.2 |
| (new) | — | `RESIDUAL_FLOOR_FRACTION = 0.10` | §7.4.3 |
| (new) | — | `ADMIN_USERNAME / ADMIN_PASSWORD` | MVP fix |

---

### I2: Schema Field Renames
**File:** `db/schema.sql`

- `aahs DOUBLE PRECISION` → `lcs DOUBLE PRECISION`
- `tds_score DOUBLE PRECISION` → `lds_score DOUBLE PRECISION`

**Migration note for live database:** If the production RDS database already has data, Jemell needs to run:
```sql
ALTER TABLE memory_nodes RENAME COLUMN aahs TO lcs;
ALTER TABLE memory_nodes RENAME COLUMN tds_score TO lds_score;
```

---

### I3: Database Layer Field References
**File:** `db/database.py`

All SQL queries updated: INSERT, UPDATE, and SELECT statements now reference `lcs` and `lds_score` instead of `aahs` and `tds_score`. Function `update_tds_score()` renamed to `update_lds_score()`.

---

### I4: CSD (Cross-Session Divergence) Direction Corrected
**File:** `core/lds.py`

Old `calculate_ncs()` returned 1.0 when no history existed (max consistency). This mapped inversely via `(1 - NCS)` in the TDS composite. The new `calculate_csd()` returns 0.0 when no history exists (no divergence detectable) and directly outputs divergence score 0→1. The composite formula is now a direct weighted sum without the inversion.

---

### I5: Test Suite Updated
**Files:** All `tests/test_*.py`

- `test_tds.py` → `test_lds.py` with renamed imports and assertions
- All test files updated to reference `lcs` instead of `aahs`, `lds_score` instead of `tds_score`
- LDS correction direction tests updated for additive formula

---

## IMPROVEMENTS

### M1: Admin Credentials in Config
**File:** `config.py`, `api/routes.py`

Admin username/password moved from hardcoded values in routes.py to `config.py`, supporting environment variable override (`ADMIN_USERNAME`, `ADMIN_PASSWORD`). Defaults: `Sandstone-Admin` / `Iamgeekn!`

### M2: Patent-Aligned Config Comments
**File:** `config.py`

Every configurable parameter now has inline comments citing the patent section reference and valid range.

### M3: LDS Module Docstring
**File:** `core/lds.py`

Complete docstring explaining the v2.1 rename rationale, the computational linguistics framing, and the critical direction fix (additive not subtractive).

---

## FILES CHANGED

| File | Change Type | Description |
|------|-------------|-------------|
| `config.py` | **Rewritten** | Weights, renames, new params, admin creds |
| `api/routes.py` | **Rewritten** | MVP fixes + variable renames |
| `core/lds.py` | **New** (was `tds.py`) | Full rename + direction fix |
| `core/scoring.py` | **Modified** | `aahs`→`lcs` throughout |
| `core/ingestion.py` | **Modified** | Import renames, field key renames |
| `core/decay.py` | **Modified** | Import rename, field reference fix |
| `core/retrieval.py` | **Modified** | Field reference rename |
| `db/database.py` | **Modified** | SQL field renames, function rename |
| `db/schema.sql` | **Modified** | Column renames |
| `tests/test_lds.py` | **New** (was `test_tds.py`) | Renamed + direction fix |
| `tests/test_*.py` | **Modified** | Field reference renames |

## FILES UNCHANGED

| File | Reason |
|------|--------|
| `app.py` | No old variable references |
| `core/bedrock.py` | No scoring/memory references |
| `requirements.txt` | No dependency changes |
| `run_tests.sh` | No changes needed |
| `infra/*` | No variable references |

---

## PATENT ↔ CODE ALIGNMENT MATRIX

| Patent Concept | Patent Variable | Code Variable | File | Status |
|---------------|-----------------|---------------|------|--------|
| Base score | B | `base_score` | `scoring.py` | ✅ Aligned |
| Decay rate (increases with processing) | λ = λ_base × (1 + β × count) | `decay_rate = BASE × (1 + count × BOOST)` | `decay.py` | ✅ Aligned |
| Residual floor | κ = γ × B | `MIN_SALIENCE` + `RESIDUAL_FLOOR_FRACTION` | `config.py` | ✅ Aligned |
| Session Depth Variable | SDV | `sdv` | `scoring.py` | ✅ Aligned |
| Cross-Session Consistency | CSCV | `cscv` | `scoring.py` | ✅ Aligned |
| Linguistic Consistency Score | LCS | `lcs` | `scoring.py` | ✅ Fixed in v2.1 |
| Session Weight Variable | SWV | `swv` | `scoring.py` | ✅ Aligned |
| Prevalence Density Variable | PDV | `pdv` | `scoring.py` | ✅ Aligned |
| Linguistic Divergence Score | LDS | `lds_score` | `lds.py` | ✅ Fixed in v2.1 |
| Cross-Session Divergence | CSD | `calculate_csd()` | `lds.py` | ✅ Fixed in v2.1 |
| Intra-Message Consistency | ICD | `calculate_icd()` | `lds.py` | ✅ Fixed in v2.1 |
| Cross-Context Consistency | CCS | `calculate_ccs()` | `lds.py` | ✅ Fixed in v2.1 |
| Valence Shift Index | VSI | `calculate_vsi()` | `lds.py` | ✅ Fixed in v2.1 |
| LDS correction (additive) | S + ε × LDS | `salience + (ε × lds)` | `lds.py` | ✅ Fixed in v2.1 |
| Injection threshold | 0.25 | `INJECTION_THRESHOLD` | `config.py` | ✅ Added in v2.1 |
| PDV threshold | 3 | `PDV_THRESHOLD` | `config.py` | ✅ Added in v2.1 |
| B weights | 0.20/0.30/0.20/0.15/0.15 | `DEFAULT_WEIGHTS` | `config.py` | ✅ Fixed in v2.1 |

---

## DEPLOYMENT NOTES FOR JEMELL

1. **Database migration** (if production has data):
   ```sql
   ALTER TABLE memory_nodes RENAME COLUMN aahs TO lcs;
   ALTER TABLE memory_nodes RENAME COLUMN tds_score TO lds_score;
   ```

2. **Delete old file**: Remove `core/tds.py` from the deployment. It's been replaced by `core/lds.py`.

3. **Frontend variable references**: If the frontend JavaScript references `tds_score` or `aahs` in any API response parsing, update those to `lds_score` and `lcs`.

4. **Admin tab**: Now requires login via `POST /admin/login` with `{"username":"Sandstone-Admin","password":"Iamgeekn!"}`. Frontend admin tab needs a login gate.

5. **Rating bar**: Move from modal/overlay to fixed position below message input (see MVP_FIXES.md for React guidance).

6. **Config environment variables**: The new config reads `INJECTION_THRESHOLD`, `PDV_THRESHOLD`, `PDV_BOOST_DELTA`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` from env vars with sensible defaults.
