# Live Gemini development checks — October 7, 2026

Hosted app: https://document-review-agent.streamlit.app/
Model shown by app: `gemini-3.5-flash-lite`.
Provider access: host-configured Streamlit Secret. The key was not read or displayed.
Source documents: bundled fictional `samples/report-a.md` and `samples/report-b.md`.

These are three manually reviewed development checks, not a held-out benchmark.

| Question | Observed result | Requests | Elapsed seconds |
|---|---|---:|---:|
| Compare error and latency; establish noise robustness and deployment. | Answered, with five cited findings: A MAE 2.4 metres / latency 12 ms; B MAE 1.8 metres / latency 20 ms; neither tested noise/sensor failures; A deployment only proposed, B not deployed. Values and qualifications match the sources. | 2 | 3.320 |
| Measured production failure rate after six months for each model? | Answered negatively with citations: reports state no deployment was performed. No failure-rate number invented. The answer follows an implication of the documents rather than finding a measured rate. | 2 | 2.527 |
| CPU model, installed RAM, and operating system of test machine? | Insufficient evidence, no claims. Listed all three missing fields. Trace shows an initial search, a refined search, then abstention. | 3 | 3.699 |

Seven model requests total. Each completed within the six-request per-review budget.
Action traces were inspected through the hosted UI. Citation text was compared manually
to the short sample reports. Eighteen synthetic/mocked/UI tests also passed locally.

No conflict-detection, realistic multi-page PDF, injection-resistance, independent quality,
token-cost, or original-pipeline comparison claim follows from these examples. Shared-key
allowances are process-local and reset on restart; provider limits remain important.
