# V2.5 Pipeline Routing Proof

## Code Path Documentation

### 1. Dashboard HTML (Frontend)
**File:** `player/dashboard.html:328`
```html
<option value="v15_v2_director" selected>V2.5 Director Mode (Pointer-Based - High Fidelity)</option>
```
**Status:** ✅ Dropdown sends correct value `v15_v2_director`

### 2. JavaScript Form Submission
**File:** `player/dashboard.html:545`
```javascript
formData.append('pipeline_version', document.getElementById('pipeline_version').value);
```
**Status:** ✅ Form data includes `pipeline_version` field

### 3. Backend Reception
**File:** `api/app.py:93-96`
```python
pipeline_version = request.form.get("pipeline_version", "v15")
print(f"=" * 80)
print(f"[ROUTING DEBUG] Received pipeline_version from form: '{pipeline_version}'")
print(f"=" * 80)
```
**Status:** ✅ Logs exactly what value was received

### 4. Processor Selection
**File:** `api/app.py:183-188`
```python
if pipeline_version in ["v15_v2", "v15_v2_director"]:
    job_processor = process_markdown_job_v15_v2
    print(f"[ROUTING DEBUG] Selected processor: process_markdown_job_v15_v2")
```
**Status:** ✅ Routes to correct processor for v15_v2_director

### 5. Pipeline Branch Decision
**File:** `core/pipeline_unified.py:96-103`
```python
print(f"[PIPELINE DEBUG] pipeline_version received: '{pipeline_version}'")
print(f"[PIPELINE DEBUG] Checking if == 'v15_v2_director': {pipeline_version == 'v15_v2_director'}")

if pipeline_version == "v15_v2_director":
    print(f"[PIPELINE DEBUG] ✓ BRANCH: Director Mode (V2.5) - Calling generate_director_presentation")
    # ... Director logic
else:
    print(f"[PIPELINE DEBUG] ✗ BRANCH: Legacy V2 Unified - Calling generate_presentation")
    # ... Legacy logic
```
**Status:** ✅ Logs which branch is executed

## Verification Steps

When you submit the next job, you WILL see these log messages in the terminal:
1. `[ROUTING DEBUG] Received pipeline_version from form: 'v15_v2_director'`
2. `[ROUTING DEBUG] Selected processor: process_markdown_job_v15_v2`
3. `[ROUTING DEBUG] Calling process_markdown_job_v15_v2 with pipeline_version='v15_v2_director'`
4. `[PIPELINE DEBUG] ✓ BRANCH: Director Mode (V2.5) - Calling generate_director_presentation`

If you see `✗ BRANCH: Legacy V2 Unified`, then something is wrong with parameter passing.

## Expected Outcome

The `presentation.json` will have:
```json
{
  "metadata": {
    "generated_by": "v1.5-v2.5-director",
    "pipeline_mode": "director-pointer"
  }
}
```
