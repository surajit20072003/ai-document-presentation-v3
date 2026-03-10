# Validation and Retry Logic Documentation

## Current Retry Stack (BaseAgent)

Every agent inherits from `BaseAgent` which has built-in retry logic:

```python
class BaseAgent:
    structural_retries = 2   # Retry if JSON parsing fails
    semantic_retries = 1     # Retry if content validation fails
    
    def run(self, **input_data):
        while True:
            response = self.call_llm(system_prompt, user_prompt)
            
            # Step 1: Parse JSON
            try:
                output = parse_json(response)
            except JSONDecodeError:
                if structural_retries_used < 2:
                    structural_retries_used += 1
                    continue  # RETRY
                raise AgentError("JSON parse failed")
            
            # Step 2: Structural Validation
            valid, errors = self.validate_structural(output)
            if not valid:
                if structural_retries_used < 2:
                    structural_retries_used += 1
                    continue  # RETRY
                raise AgentError("Structural validation failed")
            
            # Step 3: Semantic Validation
            valid, errors = self.validate_semantic(output, input_data)
            if not valid:
                if semantic_retries_used < 1:
                    semantic_retries_used += 1
                    continue  # RETRY
                raise AgentError("Semantic validation failed")
            
            return output  # SUCCESS
```

**Maximum attempts per agent**: 4 (1 initial + 2 structural + 1 semantic)

---

## Validation Types

### 1. Structural Validation
**Purpose**: Ensure JSON has required fields

**ContentCreator checks**:
- `section_id` exists
- `narration.full_text` exists
- `narration.segments` is array
- `visual_beats` is array
- Each segment has `segment_id`, `text`
- Each beat has `beat_id`, `segment_id`

### 2. Semantic Validation
**Purpose**: Ensure content meets business rules

**ContentCreator checks**:
- Word count within budget (with 25% tolerance)
- Segment count within budget
- Segment word sum matches full_text
- Avatar layer is always visible

**RendererSpec checks**:
- Video prompts don't contain banned phrases ("etc", "various", "different")
- Prompts are sufficiently detailed (>100 words recommended)

---

## Validation Strictness Problems

### Problem 1: Banned Phrases
RendererSpec rejects prompts with common words:
```python
BANNED_PHRASES = ["etc", "various", "different", "multiple"]
```
This causes retries for normal LLM output.

### Problem 2: Word Count Precision
Even with 25% tolerance, semantic validation is strict:
```python
min_with_tolerance = int(min_words * 0.75)
if word_count < min_with_tolerance:
    errors.append("Narration too short")
```

### Problem 3: Segment Count Enforcement
```python
if len(segments) < min_segs or len(segments) > max_segs:
    errors.append("Wrong segment count")
```
LLMs naturally vary output length - strict counts cause retries.

---

## How Retries Cascade

For a single section with validation issues:

```
Attempt 1: LLM call → JSON parsed → Structural PASS → Semantic FAIL (word count low)
           ↓ retry
Attempt 2: LLM call → JSON parsed → Structural PASS → Semantic PASS
           ↓ success
```

For a section that fails repeatedly:
```
Attempt 1: LLM call → JSON parse FAIL (truncated)
           ↓ retry
Attempt 2: LLM call → JSON parse FAIL (truncated)
           ↓ retry
Attempt 3: LLM call → JSON parsed → Structural PASS → Semantic FAIL
           ↓ retry
Attempt 4: LLM call → JSON parsed → Structural PASS → Semantic PASS
           ↓ success
```

**4 LLM calls for 1 section!**

---

## The Batching + Retry Compounding

With batching enabled for a quiz section with 8 Q&A:

```
Section_8:
  ├── Batch 1 (Q&A 1-4): 1-4 LLM calls
  ├── Batch 2 (Q&A 5-8): 1-4 LLM calls
  └── Total: 2-8 LLM calls (just for this section)
```

If truncation happens and batches get smaller:
```
Section_8 with truncation recovery:
  ├── Batch 1.1: 1-4 calls
  ├── Batch 1.2: 1-4 calls
  ├── Batch 2.1: 1-4 calls
  ├── Batch 2.2: 1-4 calls
  └── Total: 4-16 LLM calls!
```

---

## Proposed Simplifications

### 1. Remove Batching
```python
MAX_QA_PAIRS_PER_BATCH = 999  # Effectively disable
MAX_SOURCE_BLOCKS_PER_BATCH = 999
```

### 2. Reduce Retry Attempts
```python
structural_retries = 1  # Was 2
semantic_retries = 0    # Was 1 - trust the LLM more
```

### 3. Relax Validation
```python
# Remove word count validation for quiz/content
# Just validate JSON structure, not content lengths
def validate_semantic(self, output, input_data):
    # Skip word count checks for now
    return True, []
```

### 4. Remove Banned Phrases
```python
# RendererSpec - remove overly strict phrase banning
BANNED_PHRASES = []  # Empty - trust LLM output
```

---

## Summary

| Issue | Current | Proposed |
|-------|---------|----------|
| Batching | 4 Q&A per batch | Disable (999) |
| Structural retries | 2 | 1 |
| Semantic retries | 1 | 0 |
| Word count validation | Strict with 25% tolerance | Remove |
| Banned phrases | "etc", "various", etc. | Remove |
| Segment count validation | Strict min/max | Remove |

This would reduce LLM calls from 30+ to ~5-10 per job.
