# IC02 Summary Prompt Quality Design

## Purpose

IC02 keyword extraction already asks the LLM to return `summary`, `flow`, `interest_label`, and `keywords`.
The stored summary is now used as source material for later post generation, so the prompt must guide `summary` toward decision-ready analysis instead of a generic recap.

## Scope

Included:

- Update only the IC02 IT keyword prompt guidance.
- Keep the existing response schema unchanged.
- Keep the existing keyword extraction, candidate filtering, Ollama call, and DB merge behavior unchanged.
- Require the summary to include practical post-generation context when it is present in the source.

Excluded:

- No DB schema change.
- No additional LLM call.
- No post generation pipeline change.
- No automatic rewrite of existing stored summaries outside a user-triggered re-run.

## Summary Guidance Contract

The prompt must tell the model that `summary` is a 3-5 sentence analysis summary for post generation.

It must ask for:

- What the technology or project is.
- Differentiators against existing alternatives.
- Practical points for developers or operators.
- Limitations, testing-stage items, caveats, or operational risks when the source contains them.
- No inferred benefits, stability claims, or facts that are not present in the source.

## Verification

Unit tests must verify that `build_it_keyword_prompt()` includes the summary guidance phrases.
The existing full `ai/post_analysis` test suite must continue to pass.
