# Paper-workflow prototype: release gate not passed

Historical report for commit 6f22ce8. The [subsequent source-selection report](source-selection-development-check-2026-10-10.md) supersedes implementation and test results below; the decision to keep v0.3.8 downloads unchanged remains current.

This implementation is **unreleased**. The distributed local edition remains v0.3.8. Do not describe the new workflow as a finished solution or as available through Check for updates.

## Implementation

Local Ollama prepares source-linked purpose, contribution, findings and limitations notes for each selected paper, then checks those notes. A session-only cache uses source SHA-256, model identity and note-format version. Checkbox changes preserve notes; Clear and process exit discard them. No new dependency, model download, disk note database or cloud call is introduced.

Question planning uses notes to find relevant terminology. Overview/per-paper questions answer each source separately from original excerpts before optional synthesis. Individual answer generation does not receive generated note prose. Final checks use original cited pages plus opening/concluding excerpts, retain or remove the original claim, and resolve citation references locally. They never rewrite a finding. Focused/comparison questions retain a joint answer step.

Preparation costs up to two requests per uncached document. Overview/per-paper questions add one generation request per selected document. Planning/synthesis use two requests, with at most eight finding checks in the native app. Actual calls are recorded; this workflow is not a speed improvement. All source excerpts and checking budgets remain bounded.

## Development evidence

The six public PDFs and manually checked source-page guide are listed in [six-paper-reading-guide.md](six-paper-reading-guide.md). Their extracted pages, prompts and model outputs were development data and informed changes. They are not a held-out benchmark. Raw PDFs/model outputs remain outside version control.

All inference used the already installed Qwen2.5 7B through the local edition's loopback Ollama endpoint; no Gemini calls or model downloads. Tests reused extracted page text to avoid repeated PDF extraction. One complete preparation run made 12 requests for six papers; later development runs restored those notes in the test harness only. The product cache is memory-only and never restores notes from disk.

Observed iterations:

- Joint synthesis could cite six files yet attribute a previously developed atlas to the current study, overstate novelty, and repeat generic background. Citation count was therefore insufficient as an acceptance criterion.
- Letting the checker rewrite findings introduced a contradictory sentence. Rewriting was removed.
- Removing generated notes from answer context reduced direct repetition of note wording, but did not eliminate source confusion or omissions.
- The final isolated-paper development run used 16 requests and approximately 36 seconds for the cached overview; its surviving findings cited four of six files. The per-paper contribution question used 16 requests and approximately 37 seconds but cited only two of six files after checks. These results fail the reading-guide acceptance criteria. Timing is specific to this desktop, not an estimate for another laptop.
- The exercise-intervention question returned no surviving claims, but was classified as a per-paper request and used ten requests (approximately eleven seconds). Abstention is encouraging; routing and unnecessary processing still need work.
- Model support decisions rejected statements despite relevant wording in supplied sources, while other decisions accepted overly broad or imprecise claims. This is not independent support verification. Some generated answers still used unexplained technical language.

## Decision and next work

Keep v0.3.8 downloads unchanged. Preserve this prototype on a development branch rather than tag a release. Automated tests exercise cache isolation/provenance, source scope, malformed citations, request accounting, explicit missing-paper slots and native controls; they do not override these failed real-paper checks.

Next acceptance work should isolate retrieval, generation and verification errors on short, independently annotated examples; measure both false acceptance and false rejection of claims; and compare candidate local models on the same reserved questions before selecting a default. Do not add another generative checking loop solely because it reports confidence. Any larger model remains an explicit optional installation decision, with hardware and download costs assessed separately.
