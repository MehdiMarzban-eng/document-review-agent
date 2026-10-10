# Source selection and draft review: development results

**Unreleased.** Main, website downloads and Check for updates remain v0.3.8. This revision improves source selection but does not meet answer-quality acceptance. No new Mac packages were built.

## Changes

Source-linked paper notes and the memory-only cache from the [previous prototype](paper-workflow-development-check-2026-10-10.md) remain. Notes guide retrieval, not answer facts. Overview/per-paper answers use separate requests for each source, with coherent abstract/opening evidence followed by concluding context, capped at 8,000 characters per paper.

The model selects labeled original sentences before generating a short finding. Python attaches their actual words, page and filename. Unknown IDs, fabricated/spliced quotations and numerals absent from selected sentences are rejected. Normalization handles whitespace and ligatures, not fuzzy matching. Multiple sentences from one passage retain all quoted spans. These guards establish provenance, not entailment.

Cross-paper synthesis receives those selected spans rather than full-paper context, and requires at least two distinct sources. Focused/comparison questions keep a joint answer step. Checking uses cited passages plus nearby same-page context, capped at 6,500 characters. Legacy answers without quotes also allow a short scoped repair search. The checker states the source position before comparing the claim; it does not rewrite findings.

Results are **Draft review**. A supported judgment is recorded as `model_supported`, never proof of truth. Contradictions, invalid checks and unchecked excess are withheld. An uncertain `not_enough_information` judgment retains an already source-quoted draft as **Needs review** with the checker's reason. This can retain a wrong statement: inspect the quotation. Checker uncertainty is not proof that evidence is missing. Invalid per-paper drafts are distinguished from empty evidence selections. Rejecting an optional overview connection does not manufacture an unanswered question. Required unresolved parts still use the original request, not invented subquestions.

No new dependencies, automatic model downloads, cloud calls or persisted note database. Six papers can use up to 28 requests initially and 16 with cached notes. This is not a laptop speed improvement.

## Observations

The public PDFs and manually inspected source-page guide are in [six-paper-reading-guide.md](six-paper-reading-guide.md). These papers/questions informed tuning; they are not held-out evaluation. Raw PDFs, extracted pages and logs remain outside version control. All inference used installed Qwen2.5 7B through local loopback Ollama. The harness reused extracted text and prior prepared notes; the product cache never restores notes from disk.

Earlier commit 6f22ce8 cited 4/6 files for overview and 2/6 for per-paper contributions after checks. Directly generated quotations often contained real words with the wrong passage ID. Sentence-ID selection removes that failure.

Latest six-paper run before final local guards:

| Question | Observed result | Requests / cached time |
| --- | --- | --- |
| Main ideas in everyday language | Six individual contributions and two connections; six files cited; one connection Needs review | 16 / 20.7 s |
| Each contribution, significance and synthesis | Six files cited; one contribution Needs review; partial because a proposed requested connection lacked distinct sources | 15 / 19.4 s |
| Six-month exercise effects on memory | Focused route; no claims; original factual clause unresolved | 2 / 1.1 s |

Timing is specific to this GPU desktop. Manual review still found unexplained terminology, incomplete significance, redundant/weak connections, and an overstated `for the first time` in the HBM answer (flagged Needs review). A prior repeat substituted background about understudied connectivity for that paper's contribution. Six citations do not establish a good answer. Earlier checker experiments falsely accepted atlas-creation and historical-attribution errors; the same small model is not a dependable semantic verifier.

Ten synthetic development fixtures are committed in `dev/support_cases.json`. One run accepted all five supported paraphrases; four deliberately unsupported claims became Needs review and one was withheld. No unsupported fixture was labeled model_supported in that run. This small, tuned set is not an accuracy score; uncertain retention includes incorrect drafts. The harness separates model-supported, needs-review, withheld and unavailable-check outcomes.

All 70 software regression tests passed, including source spans, numeric guards, quote preservation, uncertainty status, original-question gaps and distinct-source comparisons. Bundled Windows native UI smoke passed with mocked inference, no network/downloads. These checks establish software behavior, not model accuracy, new Mac compatibility, fresh-machine installation or disconnected privacy guarantees.

## Decision and next gate

Push the development work without an updater release. The next gate needs independently annotated questions reserved from tuning, separately scoring retrieval, source attribution, answer completeness, plain language and semantic false acceptance/rejection. Compare alternative already installed or explicitly user-approved local models on that same set before changing the default. A lighter model is a separate hardware tradeoff; do not silently download one or add another generative checking loop merely because it reports confidence.
