V2 Pipeline Capacity Analysis
1. Capacity Estimation
Question: How many pages can the LLM take and churn out correct accurate output without losing original content?

Answer: Approximately 10-15 pages (standard 500 words/page).

Technical Reasoning
Architecture Constraint: The V2 pipeline uses a Single LLM Call (
generate_presentation
) to produce the entire presentation JSON headers, narration, visual beats, and decision logs.
Model Limits:
Input Context: Gemini 2.0 Flash has a massive input context (1M+ tokens), so reading 50+ pages is not the issue.
Output Context: The critical bottleneck is the Output Token Limit. Even with max_tokens: 32000 set in config, practical reliable generation for complex JSON often degrades or truncates around 8k-16k tokens.
Content Expansion:
Source Text (1 page) → Narration (~500 words) + Visual Descriptions (~200 words) + JSON Overhead.
This results in ~800-1000 output tokens per input page.
Calculation: 12,000 output tokens / 800 tokens/page ≈ 15 pages.
Risk Zones
Input Length	Risk Level	Probable Outcome
1-10 Pages	🟢 Low	High fidelity, complete JSON.
10-15 Pages	🟡 Medium	Occasional summarization, risk of "lazy" visual prompts.
15-25 Pages	🔴 High	JSON Truncation (pipeline failure) or distinct loss of content as model summarizes to fit.
25+ Pages	⚫ Critical	Guaranteed failure or "Outline only" output.
2. Testing Strategy
Question: How can we test that?

Methodology
To scientifically determine the "Fidelity Drop-off Point", we should implement a Progressive Load Test.

Synthetic Dataset Generation:

Create 5 separate Markdown files with known content density:
test_5pg.md
test_10pg.md
test_15pg.md
test_20pg.md
test_30pg.md
Automated Execution:

Run the V2 Generator (
generate_presentation
) against each file.
Pass Criteria:
Valid JSON output (no parse errors).
Schema validation passes.
Fidelity Scoring (The "Accuracy" Check): Since "loosing original content" is the concern, we measure Recall:

Algorithm:
Extract all unique distinct facts/paragraphs from Source MD.
Scan Generated narration.full_text + display_text for these facts.
Score = (Found Facts / Total Source Facts) * 100%.
Note: This can be automated using a cheaper LLM (e.g., Gemini Flash) as a judge.
Proposed Tool: tools/test_capacity.py
A script that:

Takes a variable n_pages.
Generates dummy educational content (repeating distinct chapters).
Runs the generator.
Reports: Token Usage, JSON Validity, and Content Length Ratio (Output Words / Input Words).