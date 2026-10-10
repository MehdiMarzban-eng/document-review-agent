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
            self.assertEqual(app.radio[0].value, "Upload my documents")
            self.assertTrue(app.button(key="review_start").disabled)
            app.radio[0].set_value("Try the example reports").run()
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
            app.radio[0].set_value("Try the example reports").run()
            app.checkbox(key="gemini_consent").check().run()
            app.button(key="review_start").click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["review_result"]["stop_reason"], "finished")
            allowance = app.session_state["shared_model_requests"]
            self.assertGreater(allowance, 0)
            app.button(key="clear_review").click().run()
            self.assertFalse(app.exception)
            self.assertNotIn("review_result", app.session_state)
            self.assertEqual(app.radio[0].value, "Upload my documents")
            self.assertEqual(app.text_area[0].value, "")
            self.assertFalse(app.checkbox(key="gemini_consent").value)
            self.assertEqual(app.session_state["shared_model_requests"], allowance)

    def test_source_changes_discard_previous_findings(self):
        with patch("providers.Gemini", return_value=Walkthrough()):
            app = self.app()
            app.radio[0].set_value("Try the example reports").run()
            app.checkbox(key="gemini_consent").check().run()
            app.button(key="review_start").click().run(timeout=30)
            self.assertIn("review_result", app.session_state)
            app.radio[0].set_value("Upload my documents").run()
            self.assertNotIn("review_result", app.session_state)
            self.assertEqual(app.text_area[0].value, "")


if __name__ == "__main__":
    unittest.main()
