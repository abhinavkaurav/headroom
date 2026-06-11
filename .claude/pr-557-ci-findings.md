# PR #557 CI Failure Findings

**PR:** fix: harden Copilot API auth token handling  
**Branch:** `fix/copilot-api-auth-token-handling`  
**CI run:** `26945659549` (2026-06-08)  
**Failing check:** `test (3.12)` — blocked at `ruff check . && ruff format --check .`

---

## Root Cause

The `test (3.12)` job fails during the **ruff lint/format step**, before pytest even runs.  
The other Python versions (3.10, 3.11, 3.13) pass because their matrix jobs apparently don't hit the same step order or the issue is version-agnostic but only one job is marked as required.

---

## Ruff Violations (6 errors)

### 1. `E741` — Ambiguous variable name `l`
**File:** `headroom/transforms/content_detector.py`  
**Lines:** 354, 355

```python
# Line 354
matching = sum(1 for l in lines if l.strip() and _FILE_PATH_PATTERN.match(l.strip()))
# Line 355
non_empty = sum(1 for l in lines if l.strip())
```

**Fix:** Rename `l` → `line` in both generator expressions.  
**Auto-fixable:** No (manual rename required)

---

### 2. `I001` — Unsorted/unformatted import block
**File:** `test_compress.py`  
**Line:** 22

```python
from headroom import compress, CompressConfig
```

**Fix:** Run `ruff check --select I001 --fix test_compress.py`  
**Auto-fixable:** Yes (`--fix`)

---

### 3. `I001` — Unsorted/unformatted import block
**File:** `tests/test_windows_adaptation.py`  
**Lines:** 9–16

```python
import json
import pytest

from headroom.config import DEFAULT_EXCLUDE_TOOLS
from headroom.transforms.content_detector import detect_content_type, ContentType
...
```

**Fix:** Run `ruff check --select I001 --fix tests/test_windows_adaptation.py`  
**Auto-fixable:** Yes (`--fix`)

---

### 4. `F401` — Unused import
**File:** `tests/test_windows_adaptation.py`  
**Line:** 10

```python
import pytest  # imported but never used
```

**Fix:** Remove the line.  
**Auto-fixable:** Yes (`--fix`)

---

### 5. `B007` — Loop variable not used in loop body
**File:** `tests/test_windows_adaptation.py`  
**Line:** 215

```python
for name, content in test_cases:  # `name` is never used
    result = router.compress(content)
```

**Fix:** Rename `name` → `_name`  
**Auto-fixable:** No (manual rename required)

---

## Fix Plan (when ready)

```bash
# Step 1: auto-fix the 3 fixable issues
ruff check --fix test_compress.py tests/test_windows_adaptation.py

# Step 2: manual fix E741 in content_detector.py lines 354-355
#   l → line

# Step 3: manual fix B007 in test_windows_adaptation.py line 215
#   name → _name

# Step 4: verify clean
ruff check . && ruff format --check .
```

---

## Other Notes

- `codecov/patch` also fails but that is a coverage gate, not a code error — will likely resolve once tests pass.
- The W293 (trailing whitespace in `copilot_auth.py:143`) seen in the CI log was from an earlier commit and is already absent from the current local branch.
- All other CI checks (3.10, 3.11, 3.13, docker e2e, windows/macOS native wrapper, build, commitlint) are passing.
- PR review decision: **APPROVED** — ready to merge once ruff is clean.
