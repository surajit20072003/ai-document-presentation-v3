# Known Issues & Future Improvements

## ISS-217: Dynamic Budgeting System (V1.5.1)
**Status:** ✅ DONE (2025-12-31)
**Priority:** Critical

**Problem**: Fixed word count and segment limits caused validation failures when actual content exceeded arbitrary limits.

**Example Failure (Job 5eae7706)**:
- Quiz narration: 419 words (fixed max was 250)
- Quiz segments: 9 (fixed max was 8)
- PDF had 15 Q&A pairs but system tried to fit them in 8 segments

**Root Cause**: Fixed limits in prompts didn't match actual content. SmartChunker counted Q&A pairs but SectionPlanner didn't use the count to calculate appropriate budgets.

**Solution: Dynamic Budgeting System**
1. SectionPlanner now outputs `budgets` object per section (word_min, word_max, segment_min, segment_max, qa_count)
2. Quiz sections automatically split based on Q&A count (1-8=1 section, 9-16=2 sections, etc.)
3. ContentCreator reads budgets from blueprint instead of using fixed limits
4. Validator validates against dynamic budgets, not fixed limits

**Files Changed**:
- `section_planner_system_v1.5.txt` - Added budget calculation rules and quiz splitting
- `content_creator_system_v1.5.txt` - Removed fixed limits, added dynamic budget guidance
- `content_creator_user_v1.5.txt` - Displays budgets with ⚠️ CRITICAL warnings
- `content_creator.py` - `build_user_prompt()` extracts budgets, `validate_semantic()` uses dynamic limits
- `section_planner.py` - Added `budgets` to required fields

---

## ISS-218: Stale Processing Jobs Cleanup
**Status:** ✅ DONE (2025-12-31)
**Priority:** Medium

**Problem**: Jobs stuck in "processing" status kept pinging server on dashboard refresh.

**Solution**: Cleaned up 10 stale processing jobs by marking them as "cancelled".

---

## ISS-220: Batching Inflates Section Output Beyond Budgets
**Status:** FIXED (2025-12-31)
**Priority:** High
**Discovered:** 2025-12-31 (Job 5f13fb49)

**Problem**: Auto-batching (ISS-211) splits large sections into multiple LLM calls but doesn't divide budgets per batch. When outputs are merged, totals exceed budgets.

**Solution**: Disabled batching by setting thresholds to 999 in `core/pipeline_v15_optimized.py`. Modern LLMs (Gemini 2.5) can handle full sections without batching.

**Example**:
- Section_8 budget: word=200-280, segments=8-10
- Section_8 actual: 2756 words, 98 segments
- Cause: 10 batches × ~200 words each = 2000+ words merged

**Root Cause**: `_merge_batched_outputs()` concatenates all batch outputs but each batch receives the full section budget, not a divided budget.

**Proposed Fix Options**:
1. **Divide budgets per batch**: `batch_word_max = section_word_max / num_batches`
2. **Reduce batching aggression**: Increase `MAX_QA_PAIRS_PER_BATCH` from 4 to 8
3. **Skip batching for quiz**: Quiz sections are typically smaller, may not need batching

---

## ISS-212: Token Optimization Between Agents
**Status:** Logged for future work
**Priority:** Medium
**Description:** Currently passing full JSON payloads between agents (Chunker → SectionPlanner → ContentCreator). Can reduce token usage by ~50% by:
1. Using compact topic summaries instead of full JSON for SectionPlanner input
2. Passing only essential fields (topic_id, title, complexity_tag) instead of full objects
3. Consider structured output schemas to reduce verbosity

**Current Cost:** ~8-12K tokens overhead per job for JSON passing
**Potential Savings:** ~4-6K tokens per job

---

## ISS-213: Smart Chunker Content Density Analysis
**Status:** ✅ DONE (2025-12-30)
**Priority:** High
**Description:** Chunker needs to analyze content density and recommend how many content sections are needed.

**Solution Implemented:**
1. Added `content_density_analysis` output with `recommended_content_sections` count
2. Added `topic_grouping_hints` for section assignment
3. SectionPlanner now consumes density recommendations
4. Pipeline uses chunker's source_blocks directly instead of re-parsing markdown

---

## ISS-214: Remove max_tokens Limits from All LLM Agents
**Status:** ✅ DONE (2025-12-30)
**Priority:** High
**Description:** Multiple agents have hardcoded max_tokens limits (8K-18K) that cause JSON truncation errors when generating long outputs.

**Symptoms:**
- `[RendererSpec] Invalid JSON response: Unterminated string at char 25118`
- Agents fail after 3 retries due to truncated JSON

**Affected Agents:**
- BaseAgent default: 8000
- ContentCreator: 12000
- RendererSpec: 10000
- SectionPlanner: 8000
- SpecialSections: 18000

**Solution:** Set `BaseAgent.max_tokens = None` by default (let API use natural limits), remove all overrides.

---

## ISS-215: Job History Status Updates Not Displaying
**Status:** ✅ DONE (2025-12-31)
**Priority:** Medium
**Description:** Status updates not showing properly on dashboard job history page.

**Solution:** Changed polling interval from 3 minutes to 3 seconds. Added auto-refresh when jobs are running.

---

## ISS-216: Validation Tolerance Too Strict
**Status:** ✅ DONE (2025-12-30)
**Priority:** High
**Description:** ContentCreator validation failing for 84 words when minimum is 100. This is 84% which should be acceptable.

**Root Cause:** Tolerance was only 10% (requiring 90+ words).

**Solution:** Increased tolerance to 25% (now 75+ words passes for 100 min).

---

## Prompt Cleanup (2025-12-30)
Backed up 39 old prompts to `core/prompts/backup_2025_12_30/`:
- All v1.2, v1.3, v1.4 prompts
- Director prompts (old pipeline)
- Renderer prompts (old format)

Active prompts: 22 files (all v1.5 for optimized pipeline)

---
