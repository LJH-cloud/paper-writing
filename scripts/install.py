#!/usr/bin/env python3
"""Install paper-writing and its pinned companion skill files using Python 3 only."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAIN_FILES = ("SKILL.md", "README.md", "INSTALL.md", "AGENTS.md",
              "dependencies.lock.json", "agents", "references", "scripts", "bundled-skills")
MAIN_REQUIRED_FILES = ("references/writing-principles.md", "references/review-workflows.md",
                       "references/manuscript-checks.md", "agents/openai.yaml",
                       "scripts/install.py", "dependencies.lock.json", "INSTALL.md",
                       "bundled-skills/anti-defensive-writing.md")
RECEIPT = ".paper-writing-install.json"
MAX_DOWNLOAD = 128 * 1024 * 1024
MAX_EXPANDED = 256 * 1024 * 1024


class InstallError(Exception):
    pass


def relative_path(value):
    if not isinstance(value, str) or "\\" in value or "\0" in value:
        raise InstallError("Invalid relative path: {!r}".format(value))
    parts = value.rstrip("/").split("/")
    if any(part in ("", ".", "..") or ":" in part for part in parts):
        raise InstallError("Unsafe relative path: {!r}".format(value))
    return Path(*parts)


def load_manifest(root):
    raw = (root / "dependencies.lock.json").read_bytes()
    data = json.loads(raw)
    if data.get("schema_version") != 1 or not isinstance(data.get("sources"), dict):
        raise InstallError("Unsupported dependency manifest")
    for source_name, source in data["sources"].items():
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", source_name):
            raise InstallError("Invalid source name")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*",
                            source.get("repository", "")):
            raise InstallError("Invalid upstream repository")
        if not re.fullmatch(r"[0-9a-fA-F]{40}", source.get("ref", "")):
            raise InstallError("Upstream ref must be a full 40-character commit")
        if source.get("license_path") is not None:
            relative_path(source["license_path"])
    if not isinstance(data.get("skills"), list):
        raise InstallError("Manifest skills must be a list")
    names = {"paper-writing"}
    for item in data["skills"]:
        name = item.get("name", "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) or name in names:
            raise InstallError("Invalid or duplicate skill name: {!r}".format(name))
        names.add(name)
        if "bundled_path" in item:
            if "source" in item or "path" in item:
                raise InstallError("A skill cannot be both bundled and upstream")
            relative_path(item["bundled_path"])
        else:
            if item.get("source") not in data["sources"]:
                raise InstallError("Unknown source for " + name)
            relative_path(item.get("path"))
        for field in ("prefer_existing", "required_files"):
            if not isinstance(item.get(field, []), list):
                raise InstallError(field + " must be a list")
            for path in item.get(field, []):
                relative_path(path)
    return data, hashlib.sha256(raw).hexdigest()


def exists(path):
    return os.path.lexists(path)


def no_links(path, boundary):
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise InstallError("Symlinks are not accepted: " + str(candidate))
        if candidate == boundary:
            break


def validate_skill(path, name, boundary=None, required=()):
    no_links(path / "SKILL.md", boundary or path)
    if not path.is_dir() or not (path / "SKILL.md").is_file():
        raise InstallError("Missing regular SKILL.md in " + str(path))
    lines = (path / "SKILL.md").read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        raise InstallError("Missing YAML frontmatter in " + str(path))
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise InstallError("Unclosed YAML frontmatter in " + str(path))
    values = [line[5:].strip() for line in lines[1:end] if line.startswith("name:")]
    if len(values) != 1 or values[0] not in (name, '"' + name + '"', "'" + name + "'"):
        raise InstallError("SKILL.md name must be {!r}: {}".format(name, path))
    for entry in required:
        file = path / relative_path(entry)
        no_links(file, boundary or path)
        if not file.is_file():
            raise InstallError("Missing required file: " + str(file))


def locate(dest, item):
    for extra in item.get("prefer_existing", []):
        path = dest / relative_path(extra)
        if exists(path):
            validate_skill(path, item["name"], dest, item.get("required_files", []))
            return path, True
    return dest / item["name"], False


def ignored(path):
    return path.name in (".git", ".DS_Store", "__pycache__", "tests") or path.suffix == ".pyc"


def copy_local(source, target):
    if ignored(source):
        return
    if source.is_symlink():
        raise InstallError("Refusing bundled symlink: " + str(source))
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            copy_local(child, target / child.name)
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    else:
        raise InstallError("Missing or special local file: " + str(source))


def download(source, target):
    url = "https://codeload.github.com/{}/zip/{}".format(source["repository"], source["ref"])
    request = Request(url, headers={"User-Agent": "paper-writing-skill-installer/1"})
    with urlopen(request, timeout=60) as response, target.open("wb") as output:
        location = urlsplit(response.geturl())
        if location.scheme != "https" or location.hostname != "codeload.github.com":
            raise InstallError("Refusing upstream redirect outside HTTPS codeload.github.com")
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD:
                raise InstallError("Upstream archive exceeds download limit")
            output.write(chunk)


def unpack(archive, source, items, staging):
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if not members or len(members) > 100000:
            raise InstallError("Empty or excessively large archive")
        paths = [(info, relative_path(info.filename)) for info in members]
        roots = {path.parts[0] for _, path in paths}
        if len(roots) != 1:
            raise InstallError("Archive must have exactly one top-level directory")
        prefix = roots.pop()
        license_path = source.get("license_path")
        license_name = prefix + "/" + license_path if license_path else None
        license_bytes = None
        total, written = 0, set()
        for info, path in paths:
            destinations, selected = [], info.filename == license_name
            for item in items:
                base = prefix + "/" + item["path"].rstrip("/") + "/"
                if info.filename.startswith(base):
                    selected = True
                    if not info.is_dir():
                        destinations.append(staging / item["name"] / relative_path(info.filename[len(base):]))
            if not selected:
                # A selected directory must also be a real directory, never a symlink.
                selected = any(str(path) == prefix + "/" + item["path"].rstrip("/") for item in items)
            if not selected:
                continue
            mode = stat.S_IFMT(info.external_attr >> 16)
            if mode not in (0, stat.S_IFREG, stat.S_IFDIR) or (mode == stat.S_IFDIR) != info.is_dir() and mode:
                raise InstallError("Special archive entry rejected: " + info.filename)
            if info.is_dir():
                continue
            total += info.file_size
            if total > MAX_EXPANDED:
                raise InstallError("Selected archive contents exceed expansion limit")
            content = bundle.read(info)
            if info.filename == license_name:
                license_bytes = content
            for destination in destinations:
                if destination in written:
                    raise InstallError("Duplicate archive entry: " + info.filename)
                written.add(destination)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
                destination.chmod(0o755 if (info.external_attr >> 16) & 0o111 else 0o644)
        if license_name and license_bytes is None:
            raise InstallError("Upstream license missing: " + license_name)
        if license_bytes is not None:
            for item in items:
                (staging / item["name"]).mkdir(parents=True, exist_ok=True)
                (staging / item["name"] / "UPSTREAM_LICENSE").write_bytes(license_bytes)


def fingerprint(path):
    if not exists(path):
        return None
    value = path.lstat()
    return (value.st_dev, value.st_ino, value.st_mode, value.st_mtime_ns)


def publish(staging, planned, dest):
    changed, backup = [], None
    try:
        for item, original in planned:
            target = dest / item["name"]
            if fingerprint(target) != original:
                raise InstallError("Destination changed during installation: " + str(target))
            saved = None
            if original is not None:
                if backup is None:
                    base = dest / ".paper-writing-backups"
                    no_links(base, dest)
                    base.mkdir(exist_ok=True)
                    backup = Path(tempfile.mkdtemp(prefix="run-", dir=base))
                saved = backup / item["name"]
                os.replace(target, saved)
            changed.append([target, saved, False])
            os.replace(staging / item["name"], target)
            changed[-1][2] = True
    except BaseException as error:
        failures = []
        for target, saved, installed in reversed(changed):
            try:
                if installed:
                    shutil.rmtree(target)
                if saved is not None:
                    if exists(target):
                        raise InstallError("Destination occupied during rollback: " + str(target))
                    os.replace(saved, target)
            except Exception as rollback_error:
                failures.append(str(rollback_error))
        if failures:
            raise InstallError("{}; rollback needs attention: {}; backups: {}".format(error, "; ".join(failures), backup)) from error
        raise
    return backup


def run(args, root=None):
    root = ROOT if root is None else root
    manifest, digest = load_manifest(root)
    dest = Path(args.dest).expanduser().absolute()
    no_links(dest, dest)
    items = ([] if args.dependencies_only else [{"name": "paper-writing", "required_files": MAIN_REQUIRED_FILES}]) + manifest["skills"]
    planned, problems = [], []
    for item in items:
        name = item["name"]
        try:
            path, preferred = locate(dest, item)
            present = exists(path)
            valid = False
            if present:
                no_links(path, dest)
                try:
                    validate_skill(path, name, dest, item.get("required_files", []))
                    valid = True
                except (InstallError, UnicodeError):
                    if args.check or not args.replace or preferred:
                        raise
            if args.check:
                print("{} {}".format("present" if valid else "missing", name))
                if not valid:
                    problems.append(name)
            elif valid and (preferred or not args.replace or (name == "paper-writing" and path.resolve() == root.resolve())):
                print("preserved {} (existing version not verified against lock)".format(name))
            else:
                planned.append((item, fingerprint(path)))
        except (InstallError, OSError, UnicodeError) as error:
            print("invalid {}: {}".format(name, error), file=sys.stderr)
            problems.append(name)
    if problems:
        return 1
    if args.check:
        return 0
    if planned:
        dest.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".paper-writing-stage-", dir=dest) as temporary:
            staging = Path(temporary)
            for source_name, source in manifest["sources"].items():
                wanted = [item for item, _ in planned if item.get("source") == source_name]
                if wanted:
                    archive = staging / (source_name + ".zip")
                    download(source, archive)
                    unpack(archive, source, wanted, staging)
            for item, _ in planned:
                target = staging / item["name"]
                origin = {"kind": "local-project", "manifest_sha256": digest}
                if item["name"] == "paper-writing":
                    for entry in MAIN_FILES:
                        if exists(root / entry):
                            copy_local(root / entry, target / entry)
                elif "bundled_path" in item:
                    source = root / relative_path(item["bundled_path"])
                    no_links(source, root)
                    copy_local(source, target / "SKILL.md" if source.is_file() else target)
                    origin.update(kind="bundled", path=item["bundled_path"])
                else:
                    source = manifest["sources"][item["source"]]
                    origin = {key: source[key] for key in ("repository", "ref")}
                    origin.update(kind="github", path=item["path"])
                validate_skill(target, item["name"], required=item.get("required_files", []))
                (target / RECEIPT).write_text(json.dumps({"schema_version": 1, "skill": item["name"], "origin": origin}, indent=2) + "\n", encoding="utf-8")
            backup = publish(staging, planned, dest)
        for item, _ in planned:
            print("installed " + item["name"])
        if backup:
            print("Previous versions backed up to " + str(backup))
    for item in items:
        validate_skill(locate(dest, item)[0], item["name"], dest, item.get("required_files", []))
    print("All requested skill entries are available. Host tools, API credentials, and accounts are not installed.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", default=str(Path(os.environ.get("CODEX_HOME") or "~/.codex").expanduser() / "skills"), help="Skill directory (default: $CODEX_HOME/skills or ~/.codex/skills)")
    parser.add_argument("--dependencies-only", action="store_true", help="Install companions only; useful after a generic skill installer")
    parser.add_argument("--check", action="store_true", help="Check presence and metadata offline without writing files")
    parser.add_argument("--replace", action="store_true", help="Replace existing skills with backups; preserve host system skills")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except KeyboardInterrupt:
        print("Installation interrupted.", file=sys.stderr)
        return 130
    except Exception as error:
        print("Installation failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
