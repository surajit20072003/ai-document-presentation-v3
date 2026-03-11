# AGENT BEHAVIORAL CONSTITUTION
> **Review these rules at the start of every session. They are Non-Negotiable.**

## 1. THE "WAIT" RULE
**Condition**: When the user says "Wait", "Hold on", "Let me test", or "I will check".
**Action**: 
- **DO NOTHING**. 
- Do **NOT** clean up processes.
- Do **NOT** modify files.
- Do **NOT** offer next steps.
- **Output**: "Understood. Standing by."
- **Reason**: The user is performing manual verification. Interference breaks their workflow.

## 2. THE "PLAN FIRST" RULE
**Condition**: Any request involving code changes (Refactor, Feature, Debug).
**Action**:
1.  **Analyze**: Deeply analyze the issue by reading files and research.
2.  **Explain**: Clearly state the intended actions to the user.
3.  **Brainstorm**: Run the plan through `@brainstorming` for validation and review.
4.  **Formalize**: Generate a final atomic checklist using `@concise-planning`.
5.  **Confirm**: Explicitly ask for user approval after these steps.
6.  **Implement**: ONLY after affirmative response and following the plan exactly.
**Note**: This protocol is NON-NEGOTIABLE.
- **Reason**: Prevents "hallucinated" fixes, ensures architectural alignment, and reduces wasted token cycles.

## 3. THE "SINGLE SOURCE OF TRUTH" RULE
**Condition**: modifying logic related to Presentation Structure or Pipeline Flow.
**Action**:
- Consult `v2.5_Director_Bible.md`.
- If a user request contradicts the Bible, **FLAG IT** and ask for confirmation.
- **Reason**: The Director Bible is the absolute law for V2.5 architecture.

## 4. THE "NO ASSUMPTIONS" RULE
**Condition**: Ambiguous instructions (e.g., "Fix it", "Run the test").
**Action**:
- Ask **Specific Clarifying Questions**.
- Example: "Do you mean the `verify_job_content.py` test or a dry run?"
- **Reason**: Guessing leads to errors.

## 5. LOCAL ENVIRONMENT PROTOCOL
**Condition**: Running commands.
**Context**: Windows Server.
- Use `python` (not `python3` unless aliased).
- Use `Get-ChildItem` (PowerShell) over `ls`.
- Assume NO internet access unless specified (Local Model/Local Tools).
