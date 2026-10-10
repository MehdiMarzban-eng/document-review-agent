# Selected documents and unresolved requests — October 10, 2026

Native and hosted interfaces now use document checkboxes. New documents are checked by default. The checked selection defines retrieval scope for every question; the model cannot silently narrow it. Empty selection disables review. Selection changes invalidate prior results. The native app preserves existing choices when files are added.

The former “Could not establish from the reviewed passages” section is now “Not fully answered”. Planner/checker instructions distinguish user requests from intermediate search topics. Every displayed unresolved item must be an exact clause from the original question. If that origin check fails, the original request remains unresolved rather than displaying invented questions or silently declaring success. This is a structural safeguard, not semantic verification.

Citation IDs are restricted in model output schemas to the current evidence IDs. The existing local validator still rejects unknown citations. Correct IDs prove provenance, not factual support.

Validation: 46 regression tests passed, including the screenshot's three invented gap questions, selection scope, source exclusion, zero-selection gating and citation schema constraints. A Windows native-control smoke test passed using the existing bundled runtime and current source, with a mocked model. Packaging CI additionally runs the native flow on Windows and both Mac architectures.

Live local development check: six user-provided public neuroanatomy PDFs; installed Ollama Qwen2.5 7B; question: “Do the papers disagree about any major point, or do they mostly study different parts of the problem? Cite the passages that support your answer.” No cloud request or model download. All six files contributed available passages. An initial run failed on an unknown citation; after adding schema constraints, a second run finished in 9.922 seconds with five model requests and known citations. It remained partial and the unresolved item matched the original question.

The second run's sole finding claimed the collection did not strongly agree/disagree, citing only one paper. That does **not** substantiate a collection-wide comparison. The model's own final check failed to catch this. Checkbox scope and gap wording are fixed; dependable cross-paper comparison remains an answer-quality limitation. Do not treat a completed model check as human verification. No held-out evaluation or general reliability claim follows from these runs.
