from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from demo import Walkthrough

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def app(self, hosted=False):
        app = AppTest.from_file(str(ROOT / ("cloud_app.py" if hosted else "app.py")))
        app.secrets["GEMINI_API_KEY"] = "synthetic-test-secret"
        return app.run(timeout=30)

    def test_gemini_default_requires_documents_and_consent(self):
        with patch("providers.Gemini") as provider:
            app = self.app()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox[0].value, "Gemini API")
            self.assertEqual(app.radio(key="source_choice").value, "Upload my documents")
            self.assertTrue(app.button(key="review_start").disabled)
            app.radio(key="source_choice").set_value("Try the example reports").run()
            self.assertTrue(app.text_area[0].value)
            self.assertTrue(app.button(key="review_start").disabled)
            self.assertFalse(app.text_input)
            provider.assert_not_called()
            rendered = " ".join(str(item.value) for group in (app.markdown, app.caption, app.text, app.error) for item in group)
            self.assertNotIn("synthetic-test-secret", rendered)

    def test_cloud_review_and_clear_preserves_allowance(self):
        with patch.dict("os.environ", {"DOCUMENT_REVIEW_HOSTED": "1"}), patch("providers.Gemini", return_value=Walkthrough()):
            app = self.app(hosted=True)
            self.assertFalse(app.selectbox)
            app.radio(key="source_choice").set_value("Try the example reports").run()
            app.checkbox(key="gemini_consent").check().run()
            app.button(key="review_start").click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["review_result"]["stop_reason"], "finished")
            allowance = app.session_state["shared_model_requests"]
            self.assertGreater(allowance, 0)
            app.button(key="clear_review").click().run()
            self.assertFalse(app.exception)
            self.assertNotIn("review_result", app.session_state)
            self.assertEqual(app.radio(key="source_choice").value, "Upload my documents")
            self.assertEqual(app.text_area[0].value, "")
            self.assertFalse(app.checkbox(key="gemini_consent").value)
            self.assertEqual(app.session_state["shared_model_requests"], allowance)

    def test_source_changes_discard_previous_findings(self):
        with patch("providers.Gemini", return_value=Walkthrough()):
            app = self.app()
            app.radio(key="source_choice").set_value("Try the example reports").run()
            app.checkbox(key="gemini_consent").check().run()
            app.button(key="review_start").click().run(timeout=30)
            self.assertIn("review_result", app.session_state)
            app.radio(key="source_choice").set_value("Upload my documents").run()
            self.assertNotIn("review_result", app.session_state)
            self.assertEqual(app.text_area[0].value, "")

    def test_own_key_uses_visitor_credentials_without_shared_allowance(self):
        with patch("providers.Gemini", return_value=Walkthrough()) as provider:
            app = self.app()
            self.assertEqual(app.radio(key="gemini_key_source").value, "Use the demo's key")
            app.radio(key="source_choice").set_value("Try the example reports").run()
            app.checkbox(key="gemini_consent").check().run()
            app.radio(key="gemini_key_source").set_value("Use my own key").run()
            self.assertFalse(app.checkbox(key="gemini_consent").value)
            self.assertTrue(app.button(key="review_start").disabled)
            app.text_input(key="visitor_key").set_value("synthetic-visitor-key").run()
            app.checkbox(key="gemini_consent").check().run()
            app.button(key="review_start").click().run(timeout=30)
            self.assertFalse(app.exception)
            provider.assert_called_once_with("synthetic-visitor-key", "gemini-3.5-flash-lite")
            self.assertNotIn("shared_model_requests", app.session_state)
            app.radio(key="gemini_key_source").set_value("Use the demo's key").run()
            self.assertNotIn("review_result", app.session_state)
            self.assertNotIn("visitor_key", app.session_state)
            self.assertFalse(app.checkbox(key="gemini_consent").value)
            self.assertFalse(app.text_input)

    def test_clear_removes_visitor_key_and_restores_demo_default(self):
        app = self.app()
        app.radio(key="gemini_key_source").set_value("Use my own key").run()
        app.text_input(key="visitor_key").set_value("synthetic-visitor-key").run()
        app.button(key="clear_review").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="gemini_key_source").value, "Use the demo's key")
        self.assertNotIn("visitor_key", app.session_state)

    def test_document_checkboxes_define_scope_and_clear_selection_disables_review(self):
        def capture_scope(corpus, *args):
            self.assertEqual([doc['name'] for doc in corpus.manifest()], ['report-b.md'])
            return {'answer': None, 'error': 'Subset verified', 'model_requests': 0,
                    'elapsed_seconds': 0, 'stop_reason': 'error', 'trace': []}
        with patch('agent.review', side_effect=capture_scope) as review:
            app = self.app()
            app.radio(key='source_choice').set_value('Try the example reports').run()
            documents = [box for box in app.checkbox if box.key.startswith('selected_doc_')]
            self.assertEqual(len(documents), 2)
            self.assertTrue(all(box.value for box in documents))
            documents[0].uncheck().run()
            app.checkbox(key='gemini_consent').check().run()
            app.button(key='review_start').click().run()
            self.assertFalse(app.exception)
            review.assert_called_once()
            app.button(key='unselect_documents').click().run()
            self.assertTrue(app.button(key='review_start').disabled)
            self.assertNotIn('review_result', app.session_state)
            app.button(key='select_documents').click().run()
            self.assertTrue(all(box.value for box in app.checkbox if box.key.startswith('selected_doc_')))


if __name__ == "__main__":
    unittest.main()
