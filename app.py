"""Document-review workspace with findings and a source inspector."""
import json
import os
from pathlib import Path
import tempfile
import streamlit as st
from agent import review
from corpus import Corpus
from demo import DEMO_QUESTION
from providers import Gemini, Ollama
from shared_access import RequestLimiter, LimitedProvider


def secret_setting(name, default=""):
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


@st.cache_resource
def shared_limiter():
    return RequestLimiter()

ROOT = Path(__file__).parent
HOSTED = os.environ.get("DOCUMENT_REVIEW_HOSTED") == "1"
LOCAL_ONLY = os.environ.get("DOCUMENT_REVIEW_LOCAL_ONLY") == "1"
st.set_page_config(page_title="Document Review Agent", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
.stApp {background:#f6f8fc; color:#17243b;}
[data-testid="stMainBlockContainer"] {padding:2.4rem 2rem; max-width:1600px;}
[data-testid="stHeader"] {background:#f6f8fc;}
[data-testid="stMain"] p, [data-testid="stMain"] h1, [data-testid="stMain"] h2,
[data-testid="stMain"] h3, [data-testid="stMain"] [data-testid="stText"] {color:#17243b;}
[data-testid="stMain"] button {background:#ffffff; color:#17243b; border:1px solid #d6dfed;}
[data-testid="stMain"] button[kind="primary"] {background:#2861c9; border-color:#2861c9; color:white;}
[data-testid="stMain"] button[kind="primary"] p {color:white;}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display:none;}
h1 {font-size:2.1rem !important; letter-spacing:-.06rem;}
h2 {font-size:1.3rem !important;}
h3 {font-size:1.05rem !important;}
.eyebrow {color:#4772b7; font-size:.73rem; font-weight:700; letter-spacing:.15rem;}
.st-key-review_brief, .st-key-evidence_inspector, .st-key-findings_empty
{background:white; border:1px solid #dde5f0; border-radius:14px; padding:1.4rem;}
div[class*="st-key-finding_card_"]
{background:white; border:1px solid #dde5f0; border-radius:12px; padding:1.1rem; margin-bottom:.6rem;}
[data-testid="stTextArea"] textarea {background:#f8faff; color:#17243b;}
[data-testid="stMain"] [data-testid="stCaptionContainer"] {color:#60718b;}
@media (max-width:1100px) {
[data-testid="stMainBlockContainer"] {padding:1.4rem 1rem;}
[data-testid="stHorizontalBlock"] {flex-direction:column;}
[data-testid="stColumn"] {width:100% !important; flex:1 1 100% !important;}
}
</style>
""", unsafe_allow_html=True)

def discard_review():
    st.session_state.pop("review_result", None)
    st.session_state.pop("inspected_passage", None)


def change_api_access():
    discard_review()
    st.session_state.pop("visitor_key", None)
    st.session_state["gemini_consent"] = False


st.markdown('<div class="eyebrow">DOCUMENT ANALYSIS</div>', unsafe_allow_html=True)
st.title("Document Review Agent")
st.write("Ask a question about your documents. Get findings with citations you can open and check.")
st.caption("Compare reports, check a claim, or find missing evidence.")

if HOSTED:
    with st.container(border=True):
        st.subheader("Local edition")
        st.write("For confidential files, use the local edition. Runs on your computer.")
        st.caption("No PDF file-size limit.")
        release = "https://github.com/MehdiMarzban-eng/document-review-agent/releases/download/"
        st.markdown(f"[Windows]({release}local-preview-v0.3.5/Document-Review-Setup.exe) · [Mac]({release}local-preview-v0.3.5/Document-Review-Setup.dmg)")
        st.markdown("**Setup download:** Windows **~6.3 GB** · Mac **~5 GB**")
        with st.expander("Setup details"):
            st.write("Native desktop app · Ollama + Qwen2.5 7B. No API key needed.")
            st.markdown("| Download | Windows | Mac |\n| --- | ---: | ---: |\n| App | ~40 MB | ~45 MB |\n| Ollama | ~1.47 GB | ~167 MB |\n| Qwen2.5 7B | ~4.7 GB | ~4.7 GB |")
            st.write("Windows x64; Mac Intel or Apple silicon, macOS 14+.")
            st.write("14 GB free disk space required for setup. 16 GB RAM recommended.")
            st.caption("Unsigned preview. Test with fictional documents first; local processing is not a confidentiality guarantee.")
            st.markdown("[Setup help and limitations](https://github.com/MehdiMarzban-eng/document-review-agent/blob/main/docs/local-edition.md)")

def clear_workspace():
    discard_review()
    for field in list(st.session_state):
        if field not in {"review_question", "gemini_consent", "visitor_key", "source_choice", "gemini_key_source"} and not field.startswith("uploads_"):
            continue
        st.session_state.pop(field, None)
    st.session_state["upload_epoch"] = st.session_state.get("upload_epoch", 0) + 1

uploads = []
key = model = ""
cloud_allowed = False
server_key = "" if LOCAL_ONLY else secret_setting("GEMINI_API_KEY")
shared_key = isinstance(server_key, str) and bool(server_key.strip())
use_shared_key = shared_key
mode = "Local Ollama model" if LOCAL_ONLY else "Gemini API"
with st.expander("Review settings", expanded=False):
    if not HOSTED and not LOCAL_ONLY:
        mode = st.selectbox("Review engine", ["Gemini API", "Local Ollama model"], on_change=discard_review)
    if mode == "Gemini API" and shared_key:
        key_source = st.radio("Gemini API access", ["Use the demo's key", "Use my own key"],
                              key="gemini_key_source", on_change=change_api_access)
        use_shared_key = key_source == "Use the demo's key"
        st.caption("The demo key is the default. Use your own key for your own Gemini quotas and billing; it does not make uploads private.")
    budget = st.slider("Maximum model requests per review", 3, 10, 6)
    st.caption("A review stops at this limit, including the final answer request.")
    if mode == "Local Ollama model":
        model = "qwen2.5:7b" if LOCAL_ONLY else st.text_input("Installed Ollama model", placeholder="Local model name")
    elif not use_shared_key:
        model = st.text_input("Gemini model", value="gemini-3.5-flash-lite")

if mode == "Gemini API":
    st.info("Gemini review · AI findings grounded in your documents. Runs only when you choose Start review.")
    st.warning("Public preview: use public or fictional documents. Gemini receives your question, retrieved text and document metadata.")
    if use_shared_key:
        key = server_key.strip()
        model = secret_setting("GEMINI_MODEL", "gemini-3.5-flash-lite")
        st.caption("Using the demo's Gemini key. No API key needed; shared request limits apply. For your own key, open Review settings.")
    else:
        st.caption("Using your own Gemini key. It is sent to this app’s server, kept in session memory and not saved to disk by the app. Your Google quotas and billing apply. Clear documents and review removes the entered key from current app state.")
        key = st.text_input("Gemini API key", type="password", key="visitor_key", on_change=discard_review)
else:
    if LOCAL_ONLY:
        st.info("Local edition · Documents and AI processing stay on this computer in this configuration. No Google connection or API key is used.")
        st.caption("Keep this computer and exported reviews protected. Local processing does not guarantee confidentiality or correct answers. Close the local launcher to stop the app.")
    else:
        st.info("Local Ollama review · Text is sent only to Ollama at 127.0.0.1 on the computer running this app. Use an installed local model and disable Ollama cloud features separately before reviewing.")


def change_source():
    discard_review()
    st.session_state["review_question"] = DEMO_QUESTION if st.session_state["source_choice"] == "Try the example reports" else ""


st.subheader("1. Choose your documents")
source_choice = st.radio("Document source", ["Upload my documents", "Try the example reports"], horizontal=True,
                         key="source_choice", on_change=change_source)
use_samples = source_choice == "Try the example reports"
if use_samples:
    st.write("These are two fictional model-evaluation reports. Report A and Report B describe different error and latency results, with limitations on robustness and deployment. Ask the example question below to see the model compare their evidence.")
    for path in sorted((ROOT / "samples").glob("*.md")):
        with st.expander(path.name):
            st.text(path.read_text(encoding="utf-8"))
else:
    uploads = st.file_uploader("Upload 1–8 documents", type=["pdf", "txt", "md"], accept_multiple_files=True,
                               key=f"uploads_{st.session_state.get('upload_epoch', 0)}", on_change=discard_review)
    st.caption("Readable PDFs, TXT or MD · Up to 8 files, 20 MB each. Scanned PDFs need OCR first. " + ("Files are processed on this computer." if LOCAL_ONLY else "Selecting a file uploads it to the hosting server immediately."))
    if uploads:
        st.caption(f"{len(uploads)} document(s) selected")

st.subheader("2. Ask a question")
st.session_state.setdefault("review_question", DEMO_QUESTION if use_samples else "")
question = st.text_area("What would you like to find out?",
                        placeholder="Example: What evidence supports the main conclusion, and what limitations are reported?",
                        max_chars=2000, height=110, key="review_question", on_change=discard_review)
if use_samples and not question:
    st.caption("Example question: " + DEMO_QUESTION)
if mode == "Gemini API":
    cloud_allowed = st.checkbox("I agree to send my question, document metadata and retrieved text to Google Gemini.", key="gemini_consent")
ready = bool(question.strip()) and bool(use_samples or uploads) and (
    bool(key) and cloud_allowed if mode == "Gemini API" else bool(model.strip()))
if not ready:
    st.caption("Choose documents, enter a question, and complete the model settings and consent above to begin.")
run_review = st.button("Start review with Gemini" if mode == "Gemini API" else "Start local review",
                       type="primary", key="review_start", disabled=not ready, use_container_width=True)

findings_column, evidence_column = st.columns([1.65, 1], gap="large")
with findings_column:
    if run_review:
        st.session_state.pop("review_result", None)
        st.session_state.pop("inspected_passage", None)
        try:
            if mode == "Gemini API" and (not cloud_allowed or not key):
                raise ValueError("Enter a key and enable sending retrieved text to Gemini.")
            if len(uploads) > 8:
                raise ValueError("Supply at most eight documents.")
            with tempfile.TemporaryDirectory(prefix="document-review-") as temporary:
                if use_samples:
                    paths = sorted((ROOT / "samples").glob("*.md"))
                else:
                    paths = []
                    for number, upload in enumerate(uploads):
                        if upload.size > 20 * 1024 * 1024:
                            raise ValueError("Each document must be at most 20 MB.")
                        folder = Path(temporary) / str(number)
                        folder.mkdir()
                        path = folder / Path(upload.name.replace("\\", "/")).name
                        path.write_bytes(upload.getvalue())
                        paths.append(path)
                corpus = Corpus.from_paths(paths)
                provider = Gemini(key, model) if mode == "Gemini API" else Ollama(model, port=11435 if LOCAL_ONLY else 11434)
                if mode == "Gemini API" and use_shared_key:
                    provider = LimitedProvider(provider, shared_limiter(), st.session_state)
                with st.spinner("Investigating the documents and preparing findings…"):
                    result = review(corpus, question, provider, budget)
                result["mode"] = mode
                st.session_state["review_result"] = result
        except (ValueError, OSError, UnicodeError) as error:
            st.error(str(error))

    st.markdown("## 3. Review the findings")
    result = st.session_state.get("review_result")
    citations = {}
    if result:
        answer = result.get("answer")
        st.caption(f"{result['mode']} · {result['model_requests']} model requests · {result['elapsed_seconds']} seconds")
        if answer:
            st.caption(answer["status"].replace("_", " ").upper())
            if not answer["claims"]:
                st.info("The retrieved evidence did not support an answer.")
            for number, claim in enumerate(answer["claims"], start=1):
                with st.container(key=f"finding_card_{number}"):
                    st.caption(f"FINDING {number:02d}")
                    st.write(claim["text"])
                    for index, citation in enumerate(claim["evidence"]):
                        identity = citation["passage_id"]
                        citations[identity] = citation
                        if st.button(f"{citation['source_name']} · page {citation['pdf_page']} ↗",
                                     key=f"cite_{number}_{index}"):
                            st.session_state["inspected_passage"] = identity
            if answer["unanswered_parts"]:
                st.markdown("### Could not establish from the reviewed passages")
                for missing in answer["unanswered_parts"]:
                    st.write(missing)
            if result.get("coverage_check") == "unavailable":
                st.caption("Final answer check was unavailable. Check the cited passages.")
        else:
            st.warning(result.get("clarification") or result.get("error") or
                       "The request budget was reached without an accepted final answer. Inspect the activity below.")
    else:
        with st.container(key="findings_empty"):
            st.markdown("### Your review will appear here")
            st.write("Ask about the evidence behind a conclusion, compare approaches, or identify what still needs testing.")
            st.caption("Findings link to source passages you can inspect alongside the review.")

with evidence_column:
    with st.container(key="evidence_inspector"):
        st.subheader("Evidence inspector")
        st.caption("SOURCE PASSAGES")
        if citations:
            selected = st.session_state.get("inspected_passage", next(iter(citations)))
            if selected not in citations:
                selected = next(iter(citations))
            citation = citations[selected]
            st.write(citation["source_name"])
            st.caption(f"PDF / logical page {citation['pdf_page']} · document label {citation['page_label']}")
            st.divider()
            st.text(citation["passage_text"])
            st.divider()
            st.caption("Resolved from the source document. Check that this passage supports the finding.")
        else:
            st.write("Select a source beneath a finding to inspect its evidence here.")
            st.caption("Page references and original source text stay together throughout the review.")

if result:
    st.divider()
    with st.expander("Review activity", expanded=False):
        st.caption(f"Stopped: {result['stop_reason']} · {result.get('decision_steps', len(result['trace']))} decision steps")
        st.json(result["trace"])
    st.caption("Check each cited passage before relying on a finding. The download contains source excerpts.")
    st.download_button("Download review and source excerpts", json.dumps(result, ensure_ascii=False, indent=2),
                       "document-review.json", "application/json")

with st.expander("Where does my document go?"):
    st.write("Uploads are processed on the computer running this app. On the public preview, that is the hosting server. Temporary working files are removed when processing ends; uploads and review excerpts can remain in session memory.")
    if LOCAL_ONLY:
        st.write("This local edition sends review requests only to its local AI engine. Google Gemini is unavailable in this configuration. Protect your computer and exported files; local processing does not establish secure erasure or protection against malicious documents.")
    else:
        st.write("Gemini receives your question, filenames, document identifiers and the passages retrieved during review. Google’s data-use and retention terms depend on its service and billing setup; the app cannot verify those settings. Disabling stored API interactions does not guarantee zero provider retention.")
        st.markdown("[Google API data-use terms](https://ai.google.dev/gemini-api/terms) · [Google retention guidance](https://ai.google.dev/gemini-api/docs/zdr)")
    st.caption("Clear documents and review removes the app’s current upload selection and review state. It cannot erase copies already sent to a provider or exported to a file, or guarantee secure erasure of server memory/disk. Exported reviews contain document excerpts.")

st.button("Clear documents and review", key="clear_review", on_click=clear_workspace)
