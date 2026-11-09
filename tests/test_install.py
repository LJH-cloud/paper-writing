"""Offline installer tests: python3 -m unittest discover -s tests -v."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
from urllib.error import URLError
import zipfile

SPEC = importlib.util.spec_from_file_location("paper_writing_installer", Path(__file__).resolve().parents[1] / "scripts" / "install.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def skill_text(name, quoted=False):
    return "---\nname: {}\ndescription: Test skill.\n---\n# Test\n".format(json.dumps(name) if quoted else name)


def write_skill(path, name):
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(skill_text(name), encoding="utf-8")


def archive(files, extras=()):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path, content in files.items():
            bundle.writestr("upstream-commit/" + path, content)
        for info, content in extras:
            bundle.writestr(info, content)
    return output.getvalue()


class Response(io.BytesIO):
    def __init__(self, content, url):
        super().__init__(content)
        self.url = url

    def geturl(self):
        return self.url


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.repo = self.home / "paper-writing"
        self.dest = self.home / "skills"
        write_skill(self.repo, "paper-writing")
        write_skill(self.repo / "bundled-skills" / "anti-defensive-writing", "anti-defensive-writing")
        for name in ("README.md", "INSTALL.md", "AGENTS.md", "agents/openai.yaml",
                     "references/guide.md", "references/writing-principles.md",
                     "references/review-workflows.md", "references/manuscript-checks.md",
                     "scripts/install.py", ".git/private", "tests/private", "references/__pycache__/private.pyc"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("local test content", encoding="utf-8")
        (self.repo / "bundled-skills/anti-defensive-writing.md").write_text(skill_text("anti-defensive-writing"), encoding="utf-8")
        self.manifest = {
            "schema_version": 1,
            "sources": {
                "nature": {"repository": "sample/nature", "ref": "a" * 40, "license_path": "LICENSE"},
                "openai": {"repository": "sample/openai", "ref": "b" * 40, "license_path": None},
            },
            "skills": [
                {"name": "anti-defensive-writing", "bundled_path": "bundled-skills/anti-defensive-writing"},
                {"name": "nature-writing", "source": "nature", "path": "skills/nature-writing", "required_files": ["manifest.yaml"]},
                {"name": "nature-shared", "source": "nature", "path": "skills/nature-shared"},
                {"name": "imagegen", "source": "openai", "path": "skills/.system/imagegen", "prefer_existing": [".system/imagegen"]},
            ],
        }
        self.save_manifest()
        self.nature_files = {
            "LICENSE": "upstream root license",
            "skills/nature-writing/SKILL.md": skill_text("nature-writing"),
            "skills/nature-writing/manifest.yaml": "name: nature-writing\n",
            "skills/nature-writing/NOTICE": "original notice",
            "skills/nature-writing/scripts/payload.py": "raise RuntimeError('must not execute')",
            "skills/nature-shared/SKILL.md": skill_text("nature-shared"),
            "skills/nature-shared/references/data.bin": b"\x00\xff\x01",
            "skills/unrequested/SKILL.md": skill_text("unrequested"),
            "install.sh": "exit 99",
        }
        self.openai_files = {
            "skills/.system/imagegen/SKILL.md": skill_text("imagegen", quoted=True),
            "skills/.system/imagegen/LICENSE.txt": "imagegen license",
        }
        self.archives = {"nature": archive(self.nature_files), "openai": archive(self.openai_files)}
        self.requests = []

    def save_manifest(self):
        (self.repo / "dependencies.lock.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def fetch(self, request, timeout):
        self.assertGreater(timeout, 0)
        url = request.full_url
        self.requests.append(url)
        for source, details in self.manifest["sources"].items():
            if url == "https://codeload.github.com/{}/zip/{}".format(details["repository"], details["ref"]):
                return Response(self.archives[source], url)
        raise AssertionError("Unexpected network request: " + url)

    def invoke(self, *options, opener=None, with_dest=True):
        output = io.StringIO()
        with mock.patch.object(installer, "ROOT", self.repo), mock.patch.object(installer, "urlopen", side_effect=opener or self.fetch), redirect_stdout(output), redirect_stderr(output):
            code = installer.main((["--dest", str(self.dest)] if with_dest else []) + list(options))
        return code, output.getvalue()

    def assert_no_installed_skills(self):
        for name in ["paper-writing"] + [item["name"] for item in self.manifest["skills"]]:
            self.assertFalse((self.dest / name).exists(), name)
        if self.dest.exists():
            self.assertEqual(list(self.dest.iterdir()), [])

    def test_clean_install_contains_all_files_licenses_and_receipts(self):
        code, output = self.invoke()
        self.assertEqual(code, 0, output)
        self.assertEqual(len(self.requests), 2, "Download each source only once")
        for item in [{"name": "paper-writing"}] + self.manifest["skills"]:
            path = self.dest / item["name"]
            installer.validate_skill(path, item["name"])
            receipt = json.loads((path / installer.RECEIPT).read_text())
            self.assertEqual(receipt["skill"], item["name"])
            self.assertNotIn(str(self.home), json.dumps(receipt))
            if "source" in item:
                self.assertEqual(receipt["origin"]["ref"], self.manifest["sources"][item["source"]]["ref"])
        self.assertEqual((self.dest / "nature-shared/references/data.bin").read_bytes(), b"\x00\xff\x01")
        self.assertEqual((self.dest / "nature-writing/UPSTREAM_LICENSE").read_text(), "upstream root license")
        self.assertTrue((self.dest / "nature-shared/UPSTREAM_LICENSE").is_file())
        self.assertEqual((self.dest / "nature-writing/NOTICE").read_text(), "original notice")
        self.assertEqual((self.dest / "imagegen/LICENSE.txt").read_text(), "imagegen license")
        self.assertFalse((self.dest / "imagegen/UPSTREAM_LICENSE").exists())
        for path in ("paper-writing/.git", "paper-writing/tests", "paper-writing/references/__pycache__", "unrequested", "install.sh"):
            self.assertFalse((self.dest / path).exists(), path)
        self.assertIn("Host tools, API credentials, and accounts are not installed", output)

    def test_repeat_preserves_custom_files_without_network(self):
        self.assertEqual(self.invoke()[0], 0)
        custom = self.dest / "nature-writing/custom.txt"
        custom.write_text("user edits")
        skill = self.dest / "nature-writing/SKILL.md"
        skill.write_text(skill_text("nature-writing") + "Custom local changes\n")
        expected = skill.read_bytes()
        code, output = self.invoke(opener=lambda *_args, **_kwargs: self.fail("Should be offline"))
        self.assertEqual(code, 0, output)
        self.assertEqual(custom.read_text(), "user edits")
        self.assertEqual(skill.read_bytes(), expected)
        self.assertIn("preserved nature-writing (existing version not verified against lock)", output)

    def test_codex_home_controls_default_destination(self):
        codex_home = self.home / "temporary-codex-home"
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
            code, output = self.invoke(with_dest=False)
        self.assertEqual(code, 0, output)
        self.assertTrue((codex_home / "skills/paper-writing/SKILL.md").is_file())
        self.assertFalse(self.dest.exists())

    def test_bundled_markdown_file_becomes_skill_entry(self):
        relative = "bundled-skills/anti-defensive-writing.md"
        (self.repo / relative).write_text(skill_text("anti-defensive-writing"), encoding="utf-8")
        self.manifest["skills"][0]["bundled_path"] = relative
        self.save_manifest()
        code, output = self.invoke()
        self.assertEqual(code, 0, output)
        self.assertEqual((self.dest / "anti-defensive-writing/SKILL.md").read_text(), skill_text("anti-defensive-writing"))
        self.assertTrue((self.dest / "paper-writing" / relative).is_file())

    def test_system_imagegen_is_preserved_even_with_replace(self):
        system = self.dest / ".system/imagegen"
        write_skill(system, "imagegen")
        (system / "custom.txt").write_text("host version")
        for options in ((), ("--replace",)):
            code, output = self.invoke(*options)
            self.assertEqual(code, 0, output)
            self.assertEqual((system / "custom.txt").read_text(), "host version")
            self.assertFalse((self.dest / "imagegen").exists())
        self.assertTrue(all("sample/nature" in url for url in self.requests))

    def test_dependencies_only_does_not_install_main(self):
        code, output = self.invoke("--dependencies-only")
        self.assertEqual(code, 0, output)
        self.assertFalse((self.dest / "paper-writing").exists())
        self.assertTrue((self.dest / "anti-defensive-writing/SKILL.md").is_file())
        self.assertEqual(self.invoke("--dependencies-only", "--check")[0], 0)
        self.assertEqual(self.invoke("--check")[0], 1)

    def test_running_from_installed_main_never_replaces_itself(self):
        self.dest = self.home
        original = (self.repo / "SKILL.md").read_bytes()
        code, output = self.invoke("--replace")
        self.assertEqual(code, 0, output)
        self.assertIn("preserved paper-writing", output)
        self.assertEqual((self.repo / "SKILL.md").read_bytes(), original)
        self.assertFalse((self.repo / installer.RECEIPT).exists())

    def test_missing_check_is_read_only_offline_and_nonzero(self):
        code, output = self.invoke("--check", opener=lambda *_args, **_kwargs: self.fail("Check must not use network"))
        self.assertEqual(code, 1)
        self.assertIn("missing nature-writing", output)
        self.assertFalse(self.dest.exists())

    def test_invalid_existing_metadata_stops_before_downloading(self):
        write_skill(self.dest / "nature-writing", "wrong-name")
        code, output = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("invalid nature-writing", output)
        self.assertEqual(self.requests, [])
        self.assertFalse((self.dest / "paper-writing").exists())
        self.assertIn("wrong-name", (self.dest / "nature-writing/SKILL.md").read_text())

    def test_incomplete_existing_skill_is_invalid(self):
        write_skill(self.dest / "nature-writing", "nature-writing")
        for options in ((), ("--check",)):
            code, output = self.invoke(*options)
            self.assertEqual(code, 1)
            self.assertIn("Missing required file", output)
        self.assertEqual(self.requests, [])

    def test_incomplete_main_is_preserved_until_explicit_replace(self):
        main = self.dest / "paper-writing"
        write_skill(main, "paper-writing")
        (main / "user-notes.txt").write_text("keep the original incomplete install")
        original = {file.name: file.read_bytes() for file in main.iterdir()}
        for options in (("--check",), ()):
            code, output = self.invoke(*options)
            self.assertEqual(code, 1, output)
            self.assertIn("invalid paper-writing", output)
            self.assertIn("Missing required file", output)
            self.assertNotIn("preserved paper-writing", output)
            self.assertEqual({file.name: file.read_bytes() for file in main.iterdir()}, original)
        self.assertEqual(self.requests, [])
        self.assertEqual(list(self.dest.iterdir()), [main])
        code, output = self.invoke("--replace")
        self.assertEqual(code, 0, output)
        installer.validate_skill(main, "paper-writing", required=installer.MAIN_REQUIRED_FILES)
        self.assertEqual(self.invoke("--check")[0], 0)
        backups = list((self.dest / ".paper-writing-backups").glob("run-*/paper-writing"))
        self.assertEqual(len(backups), 1)
        self.assertEqual({file.name: file.read_bytes() for file in backups[0].iterdir()}, original)

    def test_each_main_required_file_is_checked_before_preserving(self):
        self.assertEqual(self.invoke()[0], 0)
        self.requests.clear()
        for entry in installer.MAIN_REQUIRED_FILES:
            with self.subTest(file=entry):
                path = self.dest / "paper-writing" / entry
                content = path.read_bytes()
                path.unlink()
                try:
                    for options in (("--check",), ()):
                        code, output = self.invoke(*options)
                        self.assertEqual(code, 1, output)
                        self.assertIn("invalid paper-writing", output)
                        self.assertIn(entry, output)
                        self.assertFalse(path.exists())
                finally:
                    path.write_bytes(content)
        self.assertEqual(self.requests, [])

    def test_existing_symlink_is_rejected_without_following_it(self):
        outside = self.home / "outside"
        write_skill(outside, "nature-writing")
        self.dest.mkdir()
        (self.dest / "nature-writing").symlink_to(outside, target_is_directory=True)
        for options in ((), ("--replace",), ("--check",)):
            code, output = self.invoke(*options)
            self.assertEqual(code, 1, output)
            self.assertIn("Symlinks are not accepted", output)
        self.assertTrue((self.dest / "nature-writing").is_symlink())
        self.assertTrue((outside / "SKILL.md").is_file())
        self.assertEqual(self.requests, [])

    def test_bad_upstream_metadata_leaves_no_partial_install(self):
        self.nature_files["skills/nature-writing/SKILL.md"] = skill_text("wrong-name")
        self.archives["nature"] = archive(self.nature_files)
        code, output = self.invoke()
        self.assertEqual(code, 1, output)
        self.assert_no_installed_skills()

    def test_failed_second_download_leaves_no_partial_install(self):
        def fail_second(request, timeout):
            if "sample/openai" in request.full_url:
                raise URLError("simulated network failure")
            return self.fetch(request, timeout)
        code, output = self.invoke(opener=fail_second)
        self.assertEqual(code, 1, output)
        self.assertIn("simulated network failure", output)
        self.assert_no_installed_skills()

    def test_manifest_traversal_is_rejected_before_network(self):
        self.manifest["skills"][0]["bundled_path"] = "../outside"
        self.save_manifest()
        code, output = self.invoke()
        self.assertEqual(code, 1, output)
        self.assertEqual(self.requests, [])
        self.assertFalse(self.dest.exists())

    def test_zip_traversal_and_special_entries_are_rejected(self):
        unsafe_entries = [
            ("upstream-commit/skills/nature-writing/../../../../escape", "escaped"),
            ("/absolute/escape", "escaped"),
        ]
        for name, mode in (("link", stat.S_IFLNK | 0o777), ("fifo", stat.S_IFIFO | 0o600)):
            info = zipfile.ZipInfo("upstream-commit/skills/nature-writing/" + name)
            info.create_system = 3
            info.external_attr = mode << 16
            unsafe_entries.append((info, "../../outside"))
        for entry in unsafe_entries:
            with self.subTest(entry=entry[0]):
                self.archives["nature"] = archive(self.nature_files, [entry])
                code, output = self.invoke()
                self.assertEqual(code, 1, output)
                self.assert_no_installed_skills()
        self.assertFalse((self.home / "escape").exists())

    def test_download_and_expansion_limits_leave_no_install(self):
        for limit in ("MAX_DOWNLOAD", "MAX_EXPANDED"):
            with self.subTest(limit=limit), mock.patch.object(installer, limit, 10):
                code, output = self.invoke()
                self.assertEqual(code, 1, output)
                self.assertIn("limit", output)
                self.assert_no_installed_skills()

    def test_unsupported_archive_compression_fails_cleanly(self):
        content = bytearray(self.archives["nature"])
        content[8:10] = (99).to_bytes(2, "little")
        central = content.index(b"PK\x01\x02")
        content[central + 10:central + 12] = (99).to_bytes(2, "little")
        self.archives["nature"] = bytes(content)
        code, output = self.invoke()
        self.assertEqual(code, 1, output)
        self.assertIn("Installation failed", output)
        self.assert_no_installed_skills()

    def test_replace_keeps_recoverable_original_backup(self):
        self.assertEqual(self.invoke()[0], 0)
        marker = self.dest / "nature-writing/user-notes.txt"
        marker.write_text("must remain recoverable")
        code, output = self.invoke("--replace")
        self.assertEqual(code, 0, output)
        backups = list((self.dest / ".paper-writing-backups").glob("run-*/nature-writing/user-notes.txt"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "must remain recoverable")
        self.assertFalse(marker.exists())
        self.assertIn("Previous versions backed up", output)

    def test_publish_failure_rolls_back_replacements_and_new_skills(self):
        old = self.dest / "paper-writing"
        write_skill(old, "paper-writing")
        (old / "custom.txt").write_text("original main")
        original_replace = os.replace
        def fail_last(source, target):
            if Path(source).parent.name.startswith(".paper-writing-stage-") and Path(target).name == "imagegen":
                raise OSError("simulated publish failure")
            return original_replace(source, target)
        with mock.patch.object(installer.os, "replace", side_effect=fail_last):
            code, output = self.invoke("--replace")
        self.assertEqual(code, 1, output)
        self.assertIn("simulated publish failure", output)
        self.assertEqual((old / "custom.txt").read_text(), "original main")
        self.assertFalse((old / installer.RECEIPT).exists())
        for item in self.manifest["skills"]:
            self.assertFalse((self.dest / item["name"]).exists())
        self.assertFalse(list(self.dest.glob(".paper-writing-stage-*")))


if __name__ == "__main__":
    unittest.main()
