"""Document-review workspace with findings and a source inspector."""
import json
import os
from pathlib import Path
import tempfile
import streamlit as st
from agent import review
from corpus import Corpus
from demo import DEMO_QUESTION, Walkthrough
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
st.set_page_config(page_title="Document Review Agent", layout="wide", initial_sidebar_state="expanded")
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
[data-testid="stSidebar"] {background:#142239; color:#e8eef8;}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#e8eef8;}
[data-testid="stSidebar"] [data-testid="stExpander"] {border-color:#42516a;}
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

uploads = []
key = model = ""
cloud_allowed = False
use_samples = True
server_key = secret_setting("GEMINI_API_KEY")
shared_key = isinstance(server_key, str) and bool(server_key.strip())
with st.sidebar:
    st.markdown("### Review workspace")
    st.caption("DOCUMENT LIBRARY")
    modes = ["Offline walkthrough", "Gemini API"] if HOSTED else ["Offline walkthrough", "Local Ollama model", "Gemini API"]
    mode = st.selectbox("Review mode", modes)
    if HOSTED:
        st.caption("Public demo. Files are processed on the hosting server. Use public or fictional documents, not confidential material.")
    if mode != "Offline walkthrough":
        uploads = st.file_uploader("Add documents", type=["pdf", "txt", "md"], accept_multiple_files=True)
        st.caption("Up to 8 files · 20 MB each · readable PDF, TXT or MD")
        use_samples = st.checkbox("Use the fictional sample reports", value=not bool(uploads))
    if mode == "Offline walkthrough" or use_samples:
        st.caption("2 SAMPLE DOCUMENTS")
        for path in sorted((ROOT / "samples").glob("*.md")):
            with st.expander(path.name):
                st.text(path.read_text(encoding="utf-8"))
    else:
        st.caption(f"{len(uploads)} DOCUMENTS SELECTED")
        for upload in uploads:
            st.write(upload.name)
            st.caption(f"{upload.size / 1024:.0f} KB")
        if not uploads:
            st.caption("Add documents to begin your review.")
    st.divider()
    if mode == "Gemini API":
        st.caption("Retrieved text and your question go to Google. Free-tier content may be used to improve its products; billing and quotas determine cost.")
        if shared_key:
            key = server_key.strip()
            model = secret_setting("GEMINI_MODEL", "gemini-3.5-flash-lite")
            st.caption("Gemini is configured by the host. Shared access has request limits.")
            st.caption("Model: " + str(model))
        elif HOSTED:
            st.caption("Your key is sent to this app's server to call Gemini. It is not saved to disk. Use a key you are comfortable entrusting to this host.")
        if not shared_key:
            key = st.text_input("Gemini API key", type="password")
            model = st.text_input("Gemini model", value="gemini-3.5-flash-lite")
        cloud_allowed = st.checkbox("Send retrieved text to Gemini", key="gemini_consent")
    elif mode == "Local Ollama model":
        model = st.text_input("Installed Ollama model", placeholder="Local model name")
        st.caption("Uses your local Ollama server. No models are downloaded by this app.")
    with st.expander("Review settings"):
        budget = st.slider("Maximum model requests per review", 3, 10, 6)
        st.caption("Includes the final answer. Reviews stop at their request budget.")
    st.caption("Evolved from Document Evidence Assistant")

st.markdown('<div class="eyebrow">DOCUMENT ANALYSIS</div>', unsafe_allow_html=True)
st.title("Document Review Agent")
st.caption("Compare findings, identify gaps, and follow each conclusion back to its source.")
findings_column, evidence_column = st.columns([1.65, 1], gap="large")
with findings_column:
    with st.container(key="review_brief"):
        st.subheader("Review brief")
        if mode == "Offline walkthrough":
            st.caption("SCRIPTED WALKTHROUGH · FICTIONAL REPORTS · NO MODEL CALLS")
            question = DEMO_QUESTION
            st.write(question)
        else:
            question = st.text_area("What would you like to investigate?", value=DEMO_QUESTION,
                                    max_chars=2000, height=130)
        run_review = st.button("Review documents", type="primary", key="review_start", use_container_width=True)
    if run_review:
        st.session_state.pop("review_result", None)
        st.session_state.pop("inspected_passage", None)
        try:
            if mode == "Gemini API" and (not cloud_allowed or not key):
                raise ValueError("Enter a key and enable sending retrieved text to Gemini.")
            if len(uploads) > 8:
                raise ValueError("Supply at most eight documents.")
            with tempfile.TemporaryDirectory(prefix="document-review-") as temporary:
                if mode == "Offline walkthrough" or use_samples:
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
                provider = Walkthrough() if mode == "Offline walkthrough" else (
                    Gemini(key, model) if mode == "Gemini API" else Ollama(model))
                if mode == "Gemini API" and shared_key:
                    provider = LimitedProvider(provider, shared_limiter(), st.session_state)
                with st.spinner("Investigating the documents and preparing findings…"):
                    result = review(corpus, question, provider, budget)
                result["mode"] = mode
                st.session_state["review_result"] = result
        except (ValueError, OSError, UnicodeError) as error:
            st.error(str(error))

    st.markdown("## Findings")
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
                st.markdown("### Missing evidence")
                for missing in answer["unanswered_parts"]:
                    st.write(missing)
        else:
            st.warning(result.get("error", "The request budget was reached without an accepted final answer. Inspect the activity below."))
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
    st.download_button("Export review", json.dumps(result, ensure_ascii=False, indent=2),
                       "document-review.json", "application/json")
