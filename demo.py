"""Scripted walkthrough of the graph, explicitly not a model-quality demonstration."""
def action(name, query="", document_id="", page=1, answer=None):
    return {"action": name, "query": query, "document_id": document_id, "page": page,
            "reason": "Scripted offline demonstration step.",
            "answer": answer or {"status": "insufficient_evidence", "claims": [],
                                 "unanswered_parts": ["Not a final answer."]}}


class Walkthrough:
    """Only usable with the bundled fictional reports and predefined question."""
    is_scripted = True
    def __init__(self):
        self.step = 0

    def decide(self, system, context, schema):
        self.step += 1
        if self.step == 1:
            return action("search", "mean absolute error latency noise tested")
        if self.step == 2:
            return action("open_page", document_id=context["documents"][1]["document_id"])
        passages = context["evidence"]
        a = next(p for p in passages if p["source_name"] == "report-a.md")
        b = next(p for p in passages if p["source_name"] == "report-b.md")
        return action("finish", answer={"status": "answered", "unanswered_parts": [], "claims": [
            {"text": "On the fictional simulated cases, Model B has lower MAE (1.8 versus 2.4 metres), but higher latency (20 versus 12 milliseconds).",
             "evidence": [{"passage_id": a["id"]}, {"passage_id": b["id"]}]},
            {"text": "Neither report establishes noise robustness or production deployment.",
             "evidence": [{"passage_id": a["id"]}, {"passage_id": b["id"]}]}]})


DEMO_QUESTION = "Compare the models' error and latency. What do the reports establish about noise robustness and deployment?"
