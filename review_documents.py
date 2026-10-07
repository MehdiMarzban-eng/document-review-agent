"""CLI: offline walkthrough or explicitly selected model review."""
import argparse
import getpass
import json
from pathlib import Path
from agent import review
from corpus import Corpus
from demo import DEMO_QUESTION, Walkthrough
from providers import Gemini, Ollama


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--provider", choices=["walkthrough", "ollama", "gemini"], default="walkthrough")
    parser.add_argument("--model", default="")
    parser.add_argument("--question", default=DEMO_QUESTION)
    parser.add_argument("--max-steps", type=int, default=6)
    args = parser.parse_args()
    try:
        if args.provider == "walkthrough":
            if args.paths or args.question != DEMO_QUESTION:
                raise ValueError("The scripted walkthrough only supports its bundled question and reports.")
            paths = sorted((Path(__file__).parent / "samples").glob("*.md"))
            provider = Walkthrough()
        else:
            paths = args.paths
            provider = Ollama(args.model) if args.provider == "ollama" else Gemini(
                getpass.getpass("Gemini API key (not saved): "), args.model)
        result = review(Corpus.from_paths(paths), args.question, provider, args.max_steps)
        result["mode"] = args.provider
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["stop_reason"] == "finished" else 1
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
