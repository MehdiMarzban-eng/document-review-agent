# Document Review Agent

**Live preview:** [document-review-agent.streamlit.app](https://document-review-agent.streamlit.app/)

**Source:** [MehdiMarzban-eng/document-review-agent](https://github.com/MehdiMarzban-eng/document-review-agent)

**Current local edition:** Windows and Mac native desktop app, v0.3.7. [Download and setup details](docs/local-edition.md). The small installer prepares the app, Ollama and Qwen2.5 7B, then opens document review automatically. Use **Check for updates** in the app to install updates when you want; it does not check automatically. Existing Ollama/model files are preserved. The local edition has no fixed document-count, PDF-size, page-count or passage-count cap; available memory, processing time and model context still limit large reviews. No browser, Qt, Streamlit or UI web server. No separate Python installation or API key. Preview builds are unsigned; see setup details for privacy and verification limits.

A document analyst that can choose searches and page reads before returning cited findings. For explicit “each paper” requests, it searches across the selected files and reports which files were actually cited.
This is a separate evolution of [Document Evidence Assistant](https://document-evidence-assistant.streamlit.app/), reusing a snapshot of its PDF extraction, BM25 retrieval, and citation validation. The original project remains unchanged.

## Example

Compare two evaluation reports: which model has lower error, which has lower latency, and do either establish robustness or deployment? The bundled fictional reports illustrate those distinctions. Real model mode chooses tool actions based on retrieved evidence. The web app defaults to Gemini and has an optional example using these reports. The scripted no-model walkthrough is available only through the CLI; it is not an AI quality demonstration.

## Architecture

```text
PDF / TXT / MD -> document-qualified passages -> BM25 indexes
Question + source excerpts -> intent + information needs + alternative queries
                              | scoped, fused BM25 retrieval
                              v
                         LangGraph decision node
                                | search or open_page
                                v
                           bounded tool execution
                                | observations + evidence
                                +-> next decision
                                | finish
                                v
                       coverage/support revision -> citation validation -> findings + trace
```

The model returns a structured action envelope. Python validates the action and executes only allowlisted read-only tools; the model never executes code. These are application-level tool calls, not provider-native function-calling messages. The graph uses conditional edges to loop or stop. A fixed request ceiling includes the final-answer call, and the agent receives its remaining budget.

In model mode, question planning separates factual information needs from requests about wording or style. The selected model reformulates searches using terminology from real document excerpts. Multiple queries are fused per document; this is model-assisted lexical retrieval, not embedding search. The agent can refine searches or read pages, then revise its draft against the original question and evidence. Planning and revision count toward the same request ceiling (normally six); budgets below three use the basic tool loop. The scripted walkthrough keeps its fixed steps.

The native app can review all documents or one selected file. Ambiguous references can produce a clarification instead of silently choosing a paper. Extracted text is cached in memory for repeated questions on unchanged files and discarded when documents are cleared or replaced. Neither planning nor the final model check guarantees factual correctness or complete retrieval.

## Native local edition (Windows and Mac)

For confidential documents, download the [native local edition](https://document-review-agent.streamlit.app/#local-edition). It opens as a desktop app; it does not open a browser page or require a localhost web server. Setup installs Ollama and Qwen2.5 7B, then opens document review. The app supports any number and size of local PDFs, subject to your computer's memory and processing time. Updates are manual.

See [setup and privacy details](docs/local-edition.md).

## Developer: run the web demo from source

This is the separate Streamlit web version for contributors. It opens in a browser at a local URL; it is not how the installed native local edition runs.

Python 3.10 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open the local URL printed by Streamlit. The web demo opens in **Gemini review**:

1. Upload public/non-confidential documents, or choose **Try the example reports** to use two fictional reports with an explained comparison question.
2. Enter a question. Configure a Gemini key if the host has not provided one, and consent to sending text and metadata to Google.
3. Choose **Start review with Gemini**. Read the findings and click a citation to inspect its source passage. Clear documents and review when finished.

No model request is sent automatically. Optional Ollama access for this source-run web demo is under **Review settings**. The public preview is not suitable for confidential research; see [privacy and security boundaries](docs/privacy-and-security.md).

For the scripted no-key, no-model example, use the CLI:

```powershell
.\.venv\Scripts\python.exe review_documents.py
```

For model-driven review in this developer web demo, choose one of:

- **Local Ollama model:** install Ollama and a suitable local model yourself, then enter its installed name. The web demo only calls Ollama's API at `127.0.0.1:11434`; it never downloads a model. Disable Ollama's cloud features separately to keep inference local; loopback alone does not prevent Ollama from using its cloud service. See [local review setup](docs/local-private-review.md). Hardware, electricity, and initial model downloads are your responsibility. Not every small model can reliably follow the schema or review evidence.
- **Gemini API:** the host can configure `GEMINI_API_KEY` in Streamlit Secrets; that key is the default. Visitors can choose **Review settings → Gemini API access → Use my own key**. Without a host key, enter your own key directly. Visitor keys reach the app server and remain in session memory. Visitor access uses their Google quota/billing and does not consume the demo allowance; it never falls back to the host key. Switching access clears findings, the entered key and consent. **Clear documents and review** also restores demo access. A personal key does not make uploads private. Explicitly enable sending retrieved text. The app does not expose the host key or save entered keys to disk. The question and retrieved text go to Google; source files and absolute file paths are not submitted. Filenames and fingerprints are included in the manifest. Free-tier access and quotas are account dependent. Keep billing disabled if you require zero API charges; software cannot determine whether a supplied key belongs to a billed project. No automatic provider fallback or retry occurs.

CLI real-model example (prompts for the key; never put keys in command arguments):

```powershell
.\.venv\Scripts\python.exe review_documents.py samples/report-a.md samples/report-b.md --provider gemini --model gemini-3.5-flash-lite
```

The **hosted web app** accepts up to eight documents, 20 MB per document, 300 pages and 2,000 passages per document. These caps help bound server workload and request context. Local native use does not have fixed document-count, file-size, page-count or passage-count caps; very large batches may need substantial memory and take longer to index and review. Both modes retain bounded retrieval/model-context and request budgets. Scanned PDFs still need OCR. Uploaded web files are processed on the hosting server; temporary working files are removed after review, while upload buffers and review data remain in the app session until cleared or the session ends. Clear resets current app state, not provider copies or secure-erasure guarantees; exported JSON contains source excerpts. TXT/MD files have a single logical page. PDF citations include physical PDF pages and metadata labels.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests exercise the actual LangGraph with scripted provider responses, synthetic documents, provider transport mocks, and Streamlit's app test runner. They check cross-document provenance, refusal of unknown citations/actions, request limits, recovery from invalid page reads, provider errors, and UI gating of cloud calls. They do not measure LLM factual accuracy or resistance to prompt injection.

## Evaluation plan

Before claiming the agent improves the original pipeline, compare both on the same questions, model, and documents. Reserve independently authored questions before tuning. Score claim support manually against sources, citation correctness, unsupported-question abstention, conflict detection, requests, latency, and provider token usage when available. Include questions answerable by one search and cases requiring further investigation. An agent may increase cost without improving easy questions.

The bundled examples are development fixtures. Four [live Gemini development checks](docs/live-check-2026-10-07.md) verified a cited comparison, a negative answer about undeployed models, and abstention on missing hardware details. These are manually reviewed examples, not a held-out quality benchmark. The app records elapsed time and request count, not monetary cost or token totals.

The [October 10 natural-question development checks](docs/natural-question-development-check-2026-10-10.md) cover planning/retrieval and local Qwen runs on neuroanatomy papers. The [selected-document checks](docs/selected-document-development-check-2026-10-10.md) record checkbox scope, unresolved-request handling and a remaining weakness in cross-paper comparisons. These are development examples, not a quality benchmark.

## Limitations

- Lexical search can miss paraphrases and contradictions. Separate document BM25 scores are not directly comparable; searches retain each document's top matches.
- Extraction can damage tables, equations, and multi-column text. No OCR.
- A valid citation establishes provenance, not that its text supports a claim. Human review remains necessary.
- Prompt instructions tell the model to ignore document instructions, while tool allowlisting prevents arbitrary shell/network actions. This does not prove semantic prompt-injection resistance.
- Invalid final answers stop without displaying findings. Tool errors can be observed and corrected within the remaining budget. A request-limit stop retains the trace but returns no final answer.
- Evidence per decision is bounded to 12,000 characters including a metadata allowance, with space shared across documents. Planning excerpts use 8,000. New retrieval takes priority over old excerpts; page reads are capped at twelve passages. These bounds reduce context pressure but are not exact token counts; providers also have their own context limits.
- Public preview on Streamlit Community Cloud, using `cloud_app.py` and Python 3.12. Hosted mode omits Ollama and processes uploaded files on the server. It supports a host key or visitors' own Gemini keys. Shared-key access has process-local limits (15 requests/minute, 100/day, 30/session), including failed attempts. These reset on restart and are not a billing cap; provider quotas remain necessary. No production reliability claim. See [deployment notes](DEPLOYMENT.md).

## Reused code and provider references

`evidence_search.py` and `evidence_answers.py` are unchanged snapshots of the original project's `evidence_search.py` and `answer_question.py`, respectively, taken October 6, 2026. Only the latter's schema, citation validator, and key normalization are used by this project; its legacy CLI is not a supported entry point here. These were developed with AI assistance; this project does not establish sole independent authorship. See `ORIGIN.json` for hashes.

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini pricing and free-tier data-use notes](https://ai.google.dev/gemini-api/docs/pricing)
- [Ollama chat API](https://docs.ollama.com/api/chat)
