# Document Review Agent

**Live preview:** [document-review-agent.streamlit.app](https://document-review-agent.streamlit.app/)

**Source:** [MehdiMarzban-eng/document-review-agent](https://github.com/MehdiMarzban-eng/document-review-agent)

A document analyst that can choose searches and page reads before returning cited findings.
This is a separate evolution of [Document Evidence Assistant](https://document-evidence-assistant.streamlit.app/), reusing a snapshot of its PDF extraction, BM25 retrieval, and citation validation. The original project remains unchanged.

## Example

Compare two evaluation reports: which model has lower error, which has lower latency, and do either establish robustness or deployment? The bundled fictional reports illustrate those distinctions. Real model mode chooses tool actions based on retrieved evidence. The web app defaults to Gemini and has an optional example using these reports. The scripted no-model walkthrough is available only through the CLI; it is not an AI quality demonstration.

## Architecture

```text
PDF / TXT / MD -> document-qualified passages -> BM25 indexes
Question + document manifest -> LangGraph decision node
                                | search or open_page
                                v
                           bounded tool execution
                                | observations + evidence
                                +-> next decision
                                | finish
                                v
                       citation validation -> findings + trace
```

The model returns a structured action envelope. Python validates the action and executes only allowlisted read-only tools; the model never executes code. These are application-level tool calls, not provider-native function-calling messages. The graph uses conditional edges to loop or stop. A fixed request ceiling includes the final-answer call, and the agent receives its remaining budget.

## Run on Windows

Python 3.10 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open the local URL printed by Streamlit. The web app opens in **Gemini review**:

1. Upload public/non-confidential documents, or choose **Try the example reports** to use two fictional reports with an explained comparison question.
2. Enter a question. Configure a Gemini key if the host has not provided one, and consent to sending text and metadata to Google.
3. Choose **Start review with Gemini**. Read the findings and click a citation to inspect its source passage. Clear documents and review when finished.

No model request is sent automatically. Local Ollama is under **Review settings** in local installations. The public preview is not suitable for confidential research; see [privacy and security boundaries](docs/privacy-and-security.md).

For the scripted no-key, no-model example, use the CLI:

```powershell
.\.venv\Scripts\python.exe review_documents.py
```

For model-driven review, choose one of:

- **Local Ollama model:** install Ollama and a suitable local model yourself, then enter its installed name. The app only calls `127.0.0.1:11434`, never downloads a model, and makes no cloud requests in this mode. Hardware, electricity, and initial model downloads are your responsibility. Not every small model can reliably follow the schema or review evidence.
- **Gemini API:** the host can configure `GEMINI_API_KEY` in Streamlit Secrets; otherwise enter your own key in the password field. Explicitly enable sending retrieved text. The app does not expose the host key or save entered keys to disk. The question and retrieved text go to Google; source files and absolute file paths are not submitted. Filenames and fingerprints are included in the manifest. Free-tier access and quotas are account dependent. Keep billing disabled if you require zero API charges; software cannot determine whether a supplied key belongs to a billed project. No automatic provider fallback or retry occurs.

CLI real-model example (prompts for the key; never put keys in command arguments):

```powershell
.\.venv\Scripts\python.exe review_documents.py samples/report-a.md samples/report-b.md --provider gemini --model gemini-3.5-flash-lite
```

The UI accepts at most eight documents, 20 MB per document, 300 pages and 2,000 passages per document. Uploaded temporary working files are removed after review; upload buffers and review data remain in the app session on the server until cleared or the session ends. Clear resets current app state, not provider copies or secure-erasure guarantees; exported JSON contains source excerpts. TXT/MD files have a single logical page. PDF citations include physical PDF pages and metadata labels.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests exercise the actual LangGraph with scripted provider responses, synthetic documents, provider transport mocks, and Streamlit's app test runner. They check cross-document provenance, refusal of unknown citations/actions, request limits, recovery from invalid page reads, provider errors, and UI gating of cloud calls. They do not measure LLM factual accuracy or resistance to prompt injection.

## Evaluation plan

Before claiming the agent improves the original pipeline, compare both on the same questions, model, and documents. Reserve independently authored questions before tuning. Score claim support manually against sources, citation correctness, unsupported-question abstention, conflict detection, requests, latency, and provider token usage when available. Include questions answerable by one search and cases requiring further investigation. An agent may increase cost without improving easy questions.

The bundled examples are development fixtures. Four [live Gemini development checks](docs/live-check-2026-10-07.md) verified a cited comparison, a negative answer about undeployed models, and abstention on missing hardware details. These are manually reviewed examples, not a held-out quality benchmark. The app records elapsed time and request count, not monetary cost or token totals.

## Limitations

- Lexical search can miss paraphrases and contradictions. Separate document BM25 scores are not directly comparable; searches retain each document's top matches.
- Extraction can damage tables, equations, and multi-column text. No OCR.
- A valid citation establishes provenance, not that its text supports a claim. Human review remains necessary.
- Prompt instructions tell the model to ignore document instructions, while tool allowlisting prevents arbitrary shell/network actions. This does not prove semantic prompt-injection resistance.
- Invalid final answers stop without displaying findings. Tool errors can be observed and corrected within the remaining budget. A request-limit stop retains the trace but returns no final answer.
- Context is capped at 60,000 evidence characters; page reads are capped at twelve passages. Providers also have their own context limits.
- Public preview on Streamlit Community Cloud, using `cloud_app.py` and Python 3.12. Hosted mode omits Ollama and processes uploaded files on the server. It supports a host key or visitors' own Gemini keys. Shared-key access has process-local limits (15 requests/minute, 100/day, 30/session), including failed attempts. These reset on restart and are not a billing cap; provider quotas remain necessary. No production reliability claim. See [deployment notes](DEPLOYMENT.md).

## Reused code and provider references

`evidence_search.py` and `evidence_answers.py` are unchanged snapshots of the original project's `evidence_search.py` and `answer_question.py`, respectively, taken October 6, 2026. Only the latter's schema, citation validator, and key normalization are used by this project; its legacy CLI is not a supported entry point here. These were developed with AI assistance; this project does not establish sole independent authorship. See `ORIGIN.json` for hashes.

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini pricing and free-tier data-use notes](https://ai.google.dev/gemini-api/docs/pricing)
- [Ollama chat API](https://docs.ollama.com/api/chat)
