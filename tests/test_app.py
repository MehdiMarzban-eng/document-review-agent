from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_shared_key_stays_server_side_and_requires_consent(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.secrets["GEMINI_API_KEY"] = "synthetic-test-secret"
        app.run(timeout=30)
        app.selectbox[0].select("Gemini API").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.text_input)
        self.assertTrue(any("configured by the host" in c.value for c in app.caption))
        app.button[0].click().run()
        self.assertTrue(app.error)
        rendered = " ".join(str(item.value) for group in (app.markdown, app.caption, app.text, app.error)
                            for item in group)
        self.assertNotIn("synthetic-test-secret", rendered)

    def test_cloud_entrypoint(self):
        with patch.dict("os.environ", {"DOCUMENT_REVIEW_HOSTED": "1"}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "cloud_app.py"))
            app.secrets["TEST_MODE"] = True
            app.run(timeout=30)
            self.assertFalse(app.exception)
            self.assertNotIn("Local Ollama model", app.selectbox[0].options)
            app.button[0].click().run(timeout=30)
            self.assertEqual(app.session_state["review_result"]["stop_reason"], "finished")

    def test_offline_review_and_mode_switch(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.secrets["TEST_MODE"] = True
        app.run(timeout=30)
        self.assertFalse(app.exception)
        app.button[0].click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["review_result"]["stop_reason"], "finished")
        app.selectbox[0].select("Gemini API").run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertNotIn("review_result", app.session_state)


if __name__ == "__main__":
    unittest.main()
