"""Offline regression checks. Model responses are mocked; no tokens are consumed."""
import base64
import io
import json
import threading
import unittest
import zipfile
from unittest.mock import patch
from urllib import request, error
import app

def archive(entries):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, value in entries.items():
            z.writestr(name, value)
    return out.getvalue()

def model_response(replacement="def average(numbers):\n    return sum(numbers) / len(numbers)\n"):
    answer = {"replacement": replacement, "diagnosis": "Floor division truncates the fraction.",
              "changes": ["Use true division."], "risks": ["Empty lists are outside the existing contract."],
              "suggested_tests": [{"name": "Fractional average", "code": "assert average([1, 2]) == 1.5"}]}
    return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}], "usage": {"total_tokens": 123}}

class Repairs(unittest.TestCase):
    def setUp(self):
        self.body = {"filename": "calculator.py", "description": "Preserve fractions.",
                     "source": "placeholder",
                     "context": {"test_calculator.py": "assert average([1, 2]) == 1.5"}}
        self.body["source"] = "def average(numbers):\n    return sum(numbers) // len(numbers)\n"

    def test_valid_review_has_real_syntax_evidence_and_no_execution_claim(self):
        with patch.dict(app.SESSION, {"key": "test-key"}), patch.object(app.request, "urlopen", return_value=io.BytesIO(json.dumps(model_response()).encode())) as call:
            result = app.propose(self.body)
        self.assertEqual(result["after_check"]["state"], "passed")
        self.assertFalse(result["tests_executed"])
        self.assertIn("-    return", result["diff"])
        self.assertEqual(result["context_files"], ["test_calculator.py"])
        sent = json.loads(call.call_args.args[0].data)
        self.assertIn("test_calculator.py", sent["messages"][1]["content"])

    def test_invalid_generated_python_is_exposed_as_failed(self):
        with patch.dict(app.SESSION, {"key": "test-key"}), patch.object(app.request, "urlopen", return_value=io.BytesIO(json.dumps(model_response("def broken(")).encode())):
            self.assertEqual(app.propose(self.body)["after_check"]["state"], "failed")

    def test_truncated_model_response_cannot_be_accepted(self):
        data = model_response()
        data["choices"][0]["finish_reason"] = "length"
        with patch.dict(app.SESSION, {"key": "test-key"}), patch.object(app.request, "urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
            with self.assertRaises(app.ServiceError):
                app.propose(self.body)

    def test_malformed_model_review_is_rejected(self):
        data = {"choices": [{"message": {"content": '{"replacement":"x"}'}}]}
        with patch.dict(app.SESSION, {"key": "test-key"}), patch.object(app.request, "urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
            with self.assertRaises(app.ServiceError):
                app.propose(self.body)

    def test_source_limits_checked_before_model_call(self):
        with patch.object(app.request, "urlopen") as call:
            with self.assertRaises(ValueError):
                app.propose({**self.body, "source": "x" * 30001})
            call.assert_not_called()

    def test_context_budget(self):
        with self.assertRaises(ValueError):
            app.propose({**self.body, "context": {str(i)+".py": "x" for i in range(6)}})

    def test_syntax_checks_do_not_execute_code(self):
        self.assertEqual(app.syntax_check('raise RuntimeError("executed")', "a.py")["state"], "passed")
        self.assertEqual(app.syntax_check("{bad}", "a.json")["state"], "failed")
        self.assertEqual(app.syntax_check("const a = 1", "a.js")["state"], "not_run")

    def test_upload_filters_unsafe_and_unsupported_entries(self):
        files, skipped = app.inspect_zip(archive({"src/main.py": "print(1)", "../escape.py": "bad", ".env": "secret", "node_modules/a.js": "x", "picture.png": "binary"}))
        self.assertEqual(files, {"src/main.py": "print(1)"})
        self.assertEqual(len(skipped), 4)

    def test_export_preserves_supported_workspace(self):
        files = {"main.py": "print('fixed')\n", "tests/test.py": "assert True\n", "README.md": "notes"}
        with zipfile.ZipFile(io.BytesIO(app.project_zip(files))) as z:
            self.assertEqual({n: z.read(n).decode() for n in z.namelist()}, files)

    def test_export_rejects_path_traversal_and_secret_files(self):
        for name in ("../x.py", "C:/x.py", "/x.py", "dir/../../x.py", "credentials.json"):
            with self.assertRaises(ValueError):
                app.project_zip({name: "x"})

    def test_rate_limit_is_enforced(self):
        with patch.object(app, "EVENTS", app.defaultdict(app.deque)), patch.object(app, "RATE_LIMIT", 2):
            app.rate_limit("client")
            app.rate_limit("client")
            with self.assertRaises(app.ServiceError) as err:
                app.rate_limit("client")
            self.assertEqual(err.exception.status, 429)

class HTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_pages_and_assets_are_served(self):
        for path in ("/", "/studio", "/studio.css", "/studio.js"):
            with request.urlopen(self.url + path) as response:
                self.assertEqual(response.status, 200)
                self.assertGreater(len(response.read()), 10)

    def test_status_never_returns_key(self):
        with patch.dict(app.SESSION, {"key": "PRIVATE-TEST-SECRET"}), request.urlopen(self.url + "/api/status") as response:
            payload = response.read().decode()
            self.assertNotIn("PRIVATE-TEST-SECRET", payload)
            self.assertTrue(json.loads(payload)["configured"])

    def test_cross_origin_requests_rejected(self):
        req = request.Request(self.url + "/api/export", data=b'{"files":{"a.py":"x"}}', headers={"Content-Type": "application/json", "Origin": "https://other.invalid"})
        with self.assertRaises(error.HTTPError) as err:
            request.urlopen(req)
        self.assertEqual(err.exception.code, 400)

    def test_hosted_configuration_is_locked(self):
        req = request.Request(self.url + "/api/config", data=b'{"key":"some-long-enough-test-key"}', headers={"Content-Type": "application/json"})
        with patch.object(app, "HOSTED_DEMO", True), self.assertRaises(error.HTTPError) as err:
            request.urlopen(req)
        self.assertEqual(err.exception.code, 400)

if __name__ == "__main__":
    unittest.main()
