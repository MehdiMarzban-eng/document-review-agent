# Privacy and security boundaries

Reviewed October 9, 2026. This is a description of the current application, not a security certification or a confidentiality guarantee.

## Public Gemini preview

Use public or fictional documents. Selecting a file uploads it to the Streamlit server immediately, before the Gemini consent checkbox is checked. File buffers and results are held in the app session. The application also creates temporary files for extraction and removes its temporary directory after processing, including ordinary error exits. This is not secure erasure: process crashes, OS storage and hosting infrastructure remain outside that cleanup promise.

Gemini calls begin only after explicit consent and Start review. The provider receives the question, filenames, document fingerprints/identifiers and retrieved passages. Repeated page reads can disclose more of a document; passages may encompass an entire short document. Source files are not uploaded through Google's Files API, but this does not mean their contents stay private. The provider uses HTTPS and requests `store=false`; that disables stored interaction state, not every form of provider logging or retention.

There is no application database or shared document cache. Only the request limiter is shared across sessions. Downloaded reviews contain source text and must be handled accordingly. Clear documents and review resets uploads, the question, entered key, consent and findings in the current app state while preserving request allowances. It cannot retract provider requests, erase downloaded files or guarantee erasure of all underlying storage. The public preview has no researcher authentication, contractual institutional controls, malware scanning or independent security audit.

Google's unpaid-services terms restrict submitting sensitive, confidential or personal information, subject to the regional/service distinctions in its terms. Billing-enabled projects have different data-use provisions, but the app cannot inspect or guarantee a key's billing status, applicable contract or retention settings. A paid API by itself does not make this public preview suitable for private research.

Visitors may select their own Gemini key under Review settings. This changes provider quota and billing, not the document data flow: the key and uploads still reach the app server, and review content still goes to Google. Keys are held in session memory and omitted from exports. Switching access clears the entered key, findings and consent.

## Private research route

The [guided local edition preview](local-edition.md) packages the Python/app runtime and prepares Ollama/model downloads through a local browser setup screen. It forces local-only review mode and disables cloud features in its own Ollama process. It remains an unsigned, incompletely validated preview; do not treat download availability or mocked tests as confidential-use certification.

For sensitive work, deploy the app on an institution-controlled computer or server and select Local Ollama model under Review settings. Bind Streamlit to `127.0.0.1` for a personal installation. Install a model separately. The Ollama adapter calls only `127.0.0.1:11434`, but Ollama itself must also be configured to disable cloud features and use an installed local model. Loopback alone does not establish local inference. This avoids sending review content to Google, but does not certify the machine, model server, dependencies or network. Keep Ollama's own cloud features disabled and assess that service separately. This app does not download models.

See [local review setup](local-private-review.md) for the personal-installation route. The public Streamlit server cannot connect to a visitor’s laptop through its own loopback address.

For a multi-user research service, scope and verify these controls before making confidentiality claims:

- Institutional identity, authorization and tenant isolation; TLS on browser-to-server connections.
- Private storage/temp locations, least-privilege execution, encrypted disks, retention/deletion policy and sanitized logs.
- Sandboxed document parsing, dependency/security patching, input/resource limits and operational monitoring.
- Approved model-provider agreement and documented retention/data-use configuration, or local inference with controlled network egress.
- Tests of cross-user access and deletion behavior, incident response, backups and an independent review.

Those infrastructure and contractual controls are not implemented by this UI update. Absolute security guarantees would be misleading; claims should identify the deployment and protections actually verified.

## References

- [Google Gemini API terms](https://ai.google.dev/gemini-api/terms)
- [Google data-retention guidance](https://ai.google.dev/gemini-api/docs/zdr)
- [Google Interactions API](https://ai.google.dev/gemini-api/docs/interactions-overview)
- [Streamlit upload lifecycle](https://docs.streamlit.io/knowledge-base/using-streamlit/where-file-uploader-store-when-deleted)
