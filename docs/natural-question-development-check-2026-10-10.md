# Natural-question development checks — October 10, 2026

Implemented in the working tree and staged Windows development bundle; not published as a release. Mac packaging includes the new module, but this session did not run a Mac build. The existing installed app and hosted website are unchanged.

## Change

The selected model now plans the user's intent, presentation requirements, information needs, document scope and alternative domain searches. Real opening/summary excerpts ground that planning. Per-document rank fusion combines queries; adjacent same-page chunks preserve more of an argument. A bounded tool loop can refine retrieval before a separate claim-support and coverage revision. Structural status labels are reconciled with claims/gaps, then the original strict citation/shape validator runs. No claims, gaps or citation IDs are fabricated by that reconciliation.

The native interface adds an all-documents/single-file selector. Bare ambiguous references prompt for a document. Repeated questions reuse extracted text in memory; clearing/replacing documents clears the cache. No dependencies or model downloads were added. Default maximum remains six model requests, including planning and final revision. Evidence is bounded to 12,000 characters with a metadata allowance; planning uses 8,000.

## Verification

- 42 automated regression tests passed, including planning, scope, context bounds, invalid citations, status reconciliation, shared-key accounting, UI flows, updates and Windows archive handling.
- Native bundled-runtime smoke passed: setup-to-review, cached extraction, document selector, cited findings, source inspection, export, stale-output clearing and failure recovery. This smoke uses a scripted model.
- Live inference used the already installed `qwen2.5:7b` Q4_K_M through local Ollama on port 11435, with the six public neuroanatomy PDFs in the user's `output/pdf/neuroPaper` folder. No cloud model was called.
- The final single-paper takeaway and six-paper proposal checks both returned cited findings, completed their final checks and used five requests. Earlier development checks exercised casual paraphrasing, abstention on an unreported author salary and clarification for an ambiguous singular reference. These were development cases used during tuning, not a held-out benchmark.
- The final two live checks used approximately 1,939–6,754 prompt tokens per request with an 8,192-token context. Smaller evidence context improved reliability in this development run; this does not establish a causal performance result.
- Reused snapshot hashes still match ORIGIN.json.

## Limits observed

The structural keyword-matching problem is addressed by model-assisted query reformulation and source previews, rather than a phrase-specific substitution. Retrieval is still BM25, not vector embedding search, and can miss evidence. The same local model writes and checks answers, so its review is not independent proof of factual support. Live answers sometimes remained overly technical, shallow, or overconfident about research proposals; a completed coverage check did not guarantee every requested nuance was addressed. The implementation improves the evidence workflow but does not establish production-quality scientific synthesis or foolproof question answering. CPU-only laptop speed and Mac inference were not measured.

Raw development outputs remain local under `output/` and are ignored by Git. They include excerpts and should not be treated as publishable evaluation data by default.
