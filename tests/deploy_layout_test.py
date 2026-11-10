"""Verify build deployment bookkeeping without executing an application."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import resource_workspace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "cmake/single-app/deploy_macos.py"
spec = importlib.util.spec_from_file_location("whatson_deploy", source)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeploymentLayoutTests(unittest.TestCase):
    def test_report_is_console_output_by_default(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            deploy.emit_report({"deployed": True})
        self.assertEqual(json.loads(output.getvalue()), {"deployed": True})

    def test_explicit_report_remains_supported(self):
        with resource_workspace.temporary(ROOT, "deployment-test-") as directory:
            target = Path(directory) / "report.json"
            deploy.emit_report({"deployed": True}, target)
            self.assertEqual(json.loads(target.read_text()), {"deployed": True})

    def test_locks_live_in_resource_directory_and_distinguish_bundle_paths(self):
        with resource_workspace.temporary(ROOT, "deployment-test-") as directory:
            root = Path(directory)
            lock_dir = root / "resources" / "locks"
            app1 = root / "first" / "build" / "WhatSon.app"
            app2 = root / "second" / "build" / "WhatSon.app"
            for app in (app1, app2):
                app.parent.mkdir(parents=True)
                with deploy.deployment_lock(app, lock_dir) as locked:
                    self.assertEqual(locked, app.resolve())
            self.assertEqual(len(list(lock_dir.iterdir())), 2)
            self.assertEqual(list(app1.parent.iterdir()), [])
            self.assertEqual(list(app2.parent.iterdir()), [])

    def test_framework_copy_keeps_runtime_resources_without_development_headers(self):
        with resource_workspace.temporary(ROOT, "deployment-test-") as directory:
            root = Path(directory)
            app = root / "build" / "WhatSon.app"
            main = app / "Contents/MacOS/WhatSon"
            main.parent.mkdir(parents=True)
            main.write_bytes(b"test executable")
            framework = root / "qt/lib/QtGui.framework"
            version = framework / "Versions/A"
            for folder in ("Headers", "PrivateHeaders", "Modules", "Resources"):
                (version / folder).mkdir(parents=True)
                (version / folder / "data").write_text(folder)
            (version / "QtGui").write_bytes(b"test framework")
            (framework / "Versions/Current").symlink_to("A")
            (framework / "QtGui").symlink_to("Versions/Current/QtGui")
            (framework / "Headers").symlink_to("Versions/Current/Headers")
            dependency = "@rpath/QtGui.framework/Versions/A/QtGui"
            with patch.object(deploy, "binaries", return_value=[main]), \
                 patch.object(deploy, "dependencies", side_effect=lambda p: [dependency] if p == main else []):
                deploy.complete_frameworks(app, root / "qt")
            installed = app / "Contents/Frameworks/QtGui.framework"
            self.assertEqual((installed / "QtGui").read_bytes(), b"test framework")
            self.assertEqual((installed / "Versions/A/Resources/data").read_text(), "Resources")
            for folder in ("Headers", "PrivateHeaders", "Modules"):
                self.assertFalse((installed / "Versions/A" / folder).exists())
            self.assertFalse((installed / "Headers").is_symlink())


if __name__ == "__main__":
    unittest.main()
