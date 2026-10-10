# Local document review with Ollama

Ollama runs language models on a computer you control. Once a local model is installed, inference does not require a Gemini key or a per-request API payment. Hardware, downloads and electricity still have costs; speed and answer quality depend on the model and machine.

This is a setup guide, not a verified confidentiality guarantee. Start with fictional documents and verify your environment before using sensitive research.

## Personal Windows installation

1. Install [Ollama](https://ollama.com/download) yourself. Choose and download a local model compatible with your hardware and capable of following structured instructions. The app does not install or download models.
2. Disable Ollama cloud features: set the Windows user environment variable `OLLAMA_NO_CLOUD` to `1`, then fully quit and restart Ollama so it inherits the setting. Alternatively set `"disable_ollama_cloud": true` in Ollama's `~/.ollama/server.json` configuration, preserving other configuration fields. Use an installed local model, not a cloud model.
3. Install this project's Python dependencies using the README. Start the app bound to your computer only:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
   ```

4. Open the printed localhost URL. Under **Review settings**, select **Local Ollama model** and enter the exact installed model name (use `ollama list` to see names).
5. Test with the example reports. After installation/downloads, disconnect external networking and confirm a full review still completes. This checks an offline run, not every possible behavior of your machine. An institution can enforce outbound network restrictions for stronger assurance.
6. Keep files and exports on an approved encrypted device, avoid shared accounts and synchronized folders where inappropriate, patch dependencies, and clear the review when finished. Exports include excerpts. Disk encryption and endpoint security are separate controls you must configure.

The app still processes files and keeps the current review in memory, now on your machine. It creates temporary extraction files and normally removes them after processing. Clear is not secure erasure. PDF parsing and malicious source text remain risks requiring assessment.

## Why this differs from the public preview

The public Streamlit app runs Python on its hosting server. Its `127.0.0.1` refers to that server, not the visitor's laptop. For local inference, run both this app and Ollama locally. A private institutional deployment is another option, but needs authentication, authorization, isolated storage, retention policies and operational review before accepting confidential documents.

References: [Ollama FAQ and local-only configuration](https://github.com/ollama/ollama/blob/main/docs/faq.mdx), [Ollama API introduction](https://github.com/ollama/ollama/blob/main/docs/api/introduction.mdx), [application privacy boundaries](privacy-and-security.md).
