# Local support checks

Synthetic development fixtures, not a held-out benchmark: paraphrases, historical attribution, reused resources, association versus causation, scope and overstatement.

With an already installed model and running local-edition engine:

```powershell
.venv/Scripts/python.exe dev/evaluate_support.py --port 11435 --model qwen2.5:7b
```

Use port 11434 for standard local Ollama. The script does not start services, download models or contact cloud providers. Output defaults to ignored `.test-tmp/support-development.json`. Unavailable/malformed checks are separate from semantic rejection. Model-supported is the model's opinion; Needs review can include wrong statements.
