import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "prodmate" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import report_server


class ReportServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.page = Path(self.tmp.name) / "report.html"
        self.page.write_text("<!DOCTYPE html><p>first</p>", encoding="utf-8")
        self.server = report_server.make_server(self.page)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=5) as resp:
                return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as err:
            return err.code, err.read(), dict(err.headers)

    def version(self):
        status, body, _ = self.get("/__prodmate/version")
        self.assertEqual(status, 200)
        return json.loads(body)["version"]

    def test_server_binds_localhost(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_server_serves_report(self):
        status, body, headers = self.get("/")
        self.assertEqual(status, 200)
        self.assertEqual(body, self.page.read_bytes())
        self.assertIn("no-store", headers.get("Cache-Control", ""))
        self.assertIn("text/html", headers.get("Content-Type", ""))

    def test_version_changes_after_rewrite(self):
        before = self.version()
        time.sleep(0.01)
        self.page.write_text("<!DOCTYPE html><p>second, longer</p>", encoding="utf-8")
        self.assertNotEqual(self.version(), before)

    def test_server_missing_file_is_404(self):
        self.page.unlink()
        self.assertEqual(self.get("/")[0], 404)
        self.assertEqual(self.get("/__prodmate/version")[0], 404)
        self.page.write_text("<!DOCTYPE html><p>back</p>", encoding="utf-8")
        self.assertEqual(self.get("/")[0], 200)

    def test_server_rejects_other_paths(self):
        for path in ("/x", "/../etc/passwd", "/report.json", "/%2e%2e/etc/passwd"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], 404)


if __name__ == "__main__":
    unittest.main()
