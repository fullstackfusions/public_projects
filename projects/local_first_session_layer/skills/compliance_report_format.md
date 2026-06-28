# Compliance Report Format — Procedural Memory

## Output Structure
Every compliance assessment output must follow this structure:
1. Query restatement (one sentence)
2. Applicable guideline — name, version, effective date
3. Finding — specific clause and requirement
4. Verification status — [VERIFIED / UNVERIFIED / REQUIRES_HUMAN_REVIEW]
5. Source reference — document name, section, page

## Mandatory Rules
- Never produce a compliance finding without a source reference
- If a guideline version is uncertain, mark as REQUIRES_HUMAN_REVIEW
- Capital buffer percentages must include the institution category
- Always check whether a retrieved guideline has a superseding version

## Known Environment Details
- OSFI guidelines indexed: B-20, E-13, E-23 (as of corpus build date)
- Index built from: two PDFs, 1,038 chunks, 530,702 tokens
- Reranker: BGE, top_n=30, top_k=5 default
