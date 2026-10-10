#!/usr/bin/env python3
"""Validate a complete controlled manual build and make a static Pages payload."""
import argparse
import hashlib
import html
import json
import os
import re
import contextlib
import functools
import http.server
import threading
import shutil
import stat
import subprocess
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

SCOPE = "controlled-manual-generation"
QUALIFICATION = "pending-ci"
CLOCK = "controlled-experimental"
PRODUCER_WORKFLOW = ".github/workflows/manual-build.yml"
PRIVATE_KEYS = {
    "evidence", "native_report", "native_report_path", "publication_path",
    "publication_run", "case_participants_path", "immutable_path", "app_root",
    "run", "report", "native_source_path", "source_identity_path",
}
READER_INDEX_KEYS = {
    "aliases", "audio_chunks", "audio_examples", "course_summary", "course_title",
    "edition", "features", "learning_path", "navigation", "prelude_receipts",
    "scene_chunks", "scenes", "teaching_contracts", "title",
}
READER_DEVELOPER_KEYS = {
    "audio_metadata", "authoring_identity", "canonical_inputs",
    "complete_manual", "complete_regression_run", "inventory",
    "legacy_source_sha256", "project", "projection_schema",
    "realtime_qualification", "schema_version", "source_sha256",
    "validation_scope",
}
INTERNAL_DOC_LINKS = re.compile(
    r'<a\s+href=["\'](?:BUILD|INVENTORY|DISCREPANCIES|MIGRATION|SITE_MAP)\.md["\']([^>]*)>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def safe_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("Invalid relative asset path")
    decoded = urllib.parse.unquote(value)
    if decoded.startswith("/") or re.match(r"^[A-Za-z]:", decoded):
        raise ValueError("Absolute asset path is not allowed: " + value)
    raw_parts = decoded.split("/")
    if any(part in ("", ".") for part in raw_parts):
        raise ValueError("Unsafe relative asset path: " + value)
    path = PurePosixPath(decoded)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise ValueError("Unsafe relative asset path: " + value)
    return path


def checked_source(root, relative):
    rel = safe_relative(relative)
    path = root.joinpath(*rel.parts)
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink is not allowed in published assets: " + relative)
    resolved = path.resolve(strict=True)
    if root.resolve() not in resolved.parents:
        raise ValueError("Asset escapes source checkout: " + relative)
    if not resolved.is_file():
        raise ValueError("Published asset is not a regular file: " + relative)
    return resolved


def copy_asset(root, site, relative, copied):
    rel = safe_relative(relative)
    key = rel.as_posix()
    source = checked_source(root, key)
    target = site.joinpath(*rel.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(source), str(target))
    copied.add(key)
    return target


class AssetLinks(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.values = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("src", "href") and value:
                self.values.append(value)


def local_asset_links(text):
    parser = AssetLinks()
    parser.feed(text)
    return parser.values


def css_asset_links(text):
    return re.findall(r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)|@import\s+[\"']([^\"']+)[\"']", text, re.IGNORECASE)


def scrub_public_json(value, key=None):
    """Drop build/evidence pointers while preserving browser-visible payload."""
    if isinstance(value, dict):
        result = {}
        for name, child in value.items():
            if name in PRIVATE_KEYS or name in READER_DEVELOPER_KEYS:
                continue
            cleaned = scrub_public_json(child, name)
            if cleaned is not _DROP:
                result[name] = cleaned
        return result
    if isinstance(value, list):
        return [scrub_public_json(item, key) for item in value]
    if isinstance(value, str) and re.match(r"^/(?:home|tmp|runner|workspace|var|mnt|opt|srv|etc)/", value):
        if key in ("path", "output", "value", "run", "native_report", "report") or key and key.endswith("_path"):
            return _DROP
        raise ValueError("Absolute host path found in public JSON under " + str(key))
    return value


_DROP = object()


def public_reader_index(data):
    if not isinstance(data, dict):
        raise ValueError("Reader index must be an object")
    required = {"features", "navigation", "aliases", "scenes",
                "scene_chunks", "audio_chunks", "audio_examples",
                "learning_path", "teaching_contracts", "prelude_receipts"}
    if not required.issubset(data):
        raise ValueError("Reader index is missing a runtime field")
    public = {key: data[key] for key in READER_INDEX_KEYS if key in data}
    public["features"] = [
        {key: value for key, value in feature.items() if key != "sources"}
        for feature in public["features"]
    ]
    return scrub_public_json(public)


def public_pilot(data):
    if not isinstance(data, dict) or not {"feature", "audio", "scenes"}.issubset(data):
        raise ValueError("Pilot is missing a runtime field")
    return scrub_public_json({key: data[key] for key in ("feature", "audio", "scenes")})


def write_public_json(source, target, relative):
    data = read_json(source)
    if relative == "manual/generated/reader-index.json":
        public = public_reader_index(data)
    elif relative == "manual/generated/pilot.json":
        public = public_pilot(data)
    else:
        public = scrub_public_json(data)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(public, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def json_asset_references(value, root):
    """Find manual illustration/audio references in published JSON."""
    result = set()
    def visit(node):
        if isinstance(node, dict):
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, str):
            match = re.match(r"^(?:\.\./)*(images|manual/audio)/(.+)$", node)
            if match:
                result.add(match.group(1) + "/" + match.group(2))
            elif node.startswith("audio/") and Path(root, "manual", node).is_file():
                result.add("manual/" + node)
    visit(value)
    return result


def markdown_images(path):
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    return re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)


def asset_source_from_link(repo, parent_rel, url):
    if url.startswith(("#", "//", "http:", "https:", "mailto:", "data:", "javascript:")):
        return None
    path = urllib.parse.unquote(url.split("#", 1)[0].split("?", 1)[0])
    if not path:
        return None
    if path.startswith("/") or "\\" in path or "\x00" in path:
        raise ValueError("Unsafe static page link: " + url)
    stack = list(PurePosixPath(parent_rel).parent.parts)
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not stack:
                raise ValueError("Static page link escapes site root: " + url)
            stack.pop()
        else:
            stack.append(part)
    if not stack:
        return None
    relative = PurePosixPath(*stack).as_posix()
    source = repo / relative
    if source.suffix.lower() in (".md", ".markdown"):
        return None
    return relative


def collect_public_site(repo, destination):
    """Copy only the manual's published entry points and their referenced assets."""
    repo = Path(repo).resolve(strict=True)
    site = Path(destination)
    if site.exists():
        if site.is_symlink() or not site.is_dir() or any(site.iterdir()):
            raise ValueError("Site destination must be a new empty directory")
    else:
        site.mkdir(parents=True)
    copied = set()

    fixed = [
        "_config.yml", "README.md", "cheat_sheet.html", "config_creator.html",
        "manual/index.html", "manual/manual.css", "manual/manual.js", "manual/book.js",
        "manual/generated/reader-index.json", "manual/generated/pilot.json",
    ]
    public_data = {}
    for relative in fixed:
        source = checked_source(repo, relative)
        target = site.joinpath(*PurePosixPath(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith(".json"):
            write_public_json(source, target, relative)
            public_data[relative] = read_json(target)
        else:
            text = source.read_text(encoding="utf-8")
            if relative in ("manual/index.html", "manual/book.js", "manual/manual.js"):
                text = INTERNAL_DOC_LINKS.sub(lambda match: html.unescape(match.group(2)), text)
            target.write_text(text, encoding="utf-8")
        copied.add(relative)

    # Build a root landing page without changing the authored checkout.
    (site / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="0;url=manual/">'
        '<title>Mosaic manual</title><a href="manual/">Open the Mosaic manual</a></html>\n',
        encoding="utf-8",
    )
    if (repo / "index.html").is_file():
        copy_asset(repo, site, "index.html", copied)
    else:
        copied.add("index.html")

    # HTML, CSS, and Markdown references determine the remaining public static assets.
    refs = set()
    for relative in ("manual/index.html", "cheat_sheet.html", "config_creator.html"):
        text = (site / relative).read_text(encoding="utf-8")
        links = list(local_asset_links(text))
        if relative.endswith(".css"):
            links.extend(value for pair in css_asset_links(text) for value in pair if value)
        for link in links:
            asset = asset_source_from_link(repo, relative, link)
            if asset and Path(asset).suffix.lower() in (".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff", ".woff2", ".ttf", ".ico", ".html"):
                refs.add(asset)
    for image in markdown_images(repo / "README.md"):
        asset = asset_source_from_link(repo, "README.md", image)
        if asset:
            refs.add(asset)

    # CSS files can introduce fonts and images not named by the HTML itself.
    processed_css = set()
    while True:
        pending_css = {item for item in refs if item.lower().endswith(".css")} - processed_css
        if not pending_css:
            break
        for relative in sorted(pending_css):
            processed_css.add(relative)
            css_text = checked_source(repo, relative).read_text(encoding="utf-8")
            for pair in css_asset_links(css_text):
                for link in pair:
                    if not link:
                        continue
                    asset = asset_source_from_link(repo, relative, link)
                    if asset:
                        refs.add(asset)

    reader = public_data["manual/generated/reader-index.json"]
    chunk_groups = ("scene_chunks", "audio_chunks", "prelude_receipts")
    for group in chunk_groups:
        for chunk_id, ref in reader.get(group, {}).items():
            if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
                raise ValueError("Invalid reader chunk reference: " + group + "/" + str(chunk_id))
            relative = "manual/generated/" + safe_relative(ref["path"]).as_posix()
            copied_path = copy_asset(repo, site, relative, copied)
            chunk = read_json(copied_path)
            refs.update(json_asset_references(chunk, repo))
    for relative in public_data:
        refs.update(json_asset_references(public_data[relative], repo))
    # Only learner routes, verified scene/audio chunks and referenced assets are public.
    # Full raw build reports remain in the separate developer evidence artifact.
    refs.update(("images/logo.svg",))
    for relative in sorted(refs - copied):
        copy_asset(repo, site, relative, copied)

    # Links to source-only editorial/build notes are intentionally visible as text in this
    # generated site copy; all remaining local resource links must resolve inside the payload.
    for relative in sorted(copied):
        path = site / relative
        if path.suffix.lower() not in (".html", ".css"):
            continue
        text = path.read_text(encoding="utf-8")
        links = list(local_asset_links(text))
        if path.suffix.lower() == ".css":
            links.extend(value for pair in css_asset_links(text) for value in pair if value)
        for link in links:
            asset = asset_source_from_link(site, relative, link)
            if asset is None:
                continue
            target = site / asset
            if target.is_dir() and (target / "index.html").is_file():
                continue
            if not target.is_file():
                raise ValueError("Published page references a missing local asset: " + relative + " -> " + link)
    return copied


def verify_build(repo, evidence, source_identity, audit_function=None):
    repo = Path(repo).resolve(strict=True)
    evidence = Path(evidence).resolve(strict=True)
    identity = read_json(source_identity)
    manifest_path = evidence / "manifest.json"
    manifest = read_json(manifest_path)
    if identity.get("schema_version") != 1:
        raise ValueError("Invalid frozen source identity")
    for key in ("commit_sha", "tree_sha"):
        if not isinstance(identity.get(key), str) or not re.fullmatch(r"[0-9a-f]{40}", identity[key]):
            raise ValueError("Invalid frozen Git source identity: " + key)
    if manifest.get("schema_version") != 1 or manifest.get("passed") is not True:
        raise ValueError("Manual build manifest is incomplete")
    if manifest.get("build_complete") is not False or manifest.get("manual_generation_complete") is not True:
        raise ValueError("Controlled manual generation completion markers are invalid")
    if manifest.get("validation_scope") != SCOPE or manifest.get("realtime_qualification") != QUALIFICATION:
        raise ValueError("Manual build scope does not match controlled generation")
    if manifest.get("clock_mode") != CLOCK or manifest.get("complete_regression_run") is not False:
        raise ValueError("Manual build claims an unsupported timing or regression scope")
    if manifest.get("revision") != identity["commit_sha"]:
        raise ValueError("Build manifest source commit is stale")
    if manifest.get("renderer_validated") is not True:
        raise ValueError("Browser rendering validation is missing")
    if audit_function is None:
        sys.path.insert(0, str(repo / "tools"))
        import manual_publication_verify
        audit_function = manual_publication_verify.audit_controlled_manual_generation
    audit = audit_function(evidence, require_manual_generation_complete=True)
    if audit.get("passed") is not True or audit.get("manual_generation_complete") is not True:
        raise ValueError("Strict final controlled publication audit did not pass")
    if audit.get("validation_scope") != SCOPE or audit.get("realtime_qualification") != QUALIFICATION or audit.get("complete_regression_run") is not False:
        raise ValueError("Strict final audit returned an invalid scope")
    return manifest, sha256(manifest_path), identity, audit


def parse_repo_slug(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("Invalid repository slug")
    return value


def make_artifact(repo, evidence, identity_path, output, provenance, audit_function=None):
    repo = Path(repo).resolve(strict=True)
    manifest, build_sha, identity, audit = verify_build(repo, evidence, identity_path, audit_function)
    out = Path(output)
    if out.exists():
        if out.is_symlink() or not out.is_dir() or any(out.iterdir()):
            raise ValueError("Artifact output must be a new empty directory")
    else:
        out.mkdir(parents=True)
    site = out / "manual-site"
    files = collect_public_site(repo, site)
    file_hashes = {"manual-site/" + name: sha256(site / name) for name in sorted(files)}
    pr_number = provenance.get("pr_number")
    pr_head = provenance.get("pr_head_sha")
    base_ref = provenance.get("pr_base_ref")
    if pr_number is None:
        if pr_head is not None or base_ref is not None:
            raise ValueError("Non-PR artifact cannot carry PR identity")
    elif type(pr_number) is not int or pr_number < 1 or not pr_head or not base_ref:
        raise ValueError("Incomplete PR artifact identity")
    result = {
        "schema_version": 1,
        "repository": parse_repo_slug(provenance.get("repository")),
        "producer_workflow": PRODUCER_WORKFLOW,
        "producer_run_id": int(provenance.get("producer_run_id")),
        "producer_run_attempt": int(provenance.get("producer_run_attempt")),
        "pr_number": pr_number,
        "pr_head_sha": pr_head,
        "pr_base_ref": base_ref,
        "tested_commit_sha": identity["commit_sha"],
        "tested_tree_sha": identity["tree_sha"],
        "finalized_build_manifest_sha256": build_sha,
        "validation_scope": SCOPE,
        "realtime_qualification": QUALIFICATION,
        "clock_mode": CLOCK,
        "manual_generation_complete": True,
        "complete_regression_run": False,
        "files": file_hashes,
        "audit_summary": {
            "controlled_stage_count": len(audit.get("controlled_stages", [])),
            "published_feature_count": audit.get("features"),
            "build_manifest_sha256": build_sha,
        },
    }
    (out / "manual-artifact-manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


EVIDENCE_SUFFIXES = {".json", ".jsonl", ".png", ".wav", ".mid", ".midi", ".mp3", ".ogg", ".txt", ".log", ".yaml", ".yml", ".csv"}
EVIDENCE_EXCLUDED_PARTS = {"code", "data", "application", "project", ".git", "node_modules", "__pycache__"}

def copy_evidence_tree(build, output, file_map):
    source = Path(build).resolve(strict=True)
    target_root = Path(output)
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        # Excluded private trees, including captured code and data, are
        # outside the evidence bundle contract, so their symlinks are ignored.
        # Allowed evidence remains fail-closed: never follow or archive links.
        if EVIDENCE_EXCLUDED_PARTS.intersection(relative.parts):
            continue
        if path.is_symlink():
            raise ValueError("Symlink in immutable build evidence: " + str(path))
        if not path.is_file():
            continue
        target = target_root / "build" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(path), str(target))
        file_map[target.relative_to(target_root).as_posix()] = sha256(target)


def make_evidence_bundle(build, output, source_identity=None, artifact_manifest=None, provisioning_log=None, extra_references=()):
    target = Path(output)
    if target.exists() and (target.is_symlink() or not target.is_dir() or any(target.iterdir())):
        raise ValueError("Evidence output must be a new empty directory")
    target.mkdir(parents=True, exist_ok=True)
    files, path_map = {}, {}
    build_path = Path(build).resolve() if build else None
    if build_path and build_path.is_dir():
        copy_evidence_tree(build_path, target, files)
    else:
        build_path = None
    queue, seen = [], set()
    if build_path:
        manifest_path = build_path / "manifest.json"
        if manifest_path.is_file():
            manifest = read_json(manifest_path)
            for row in manifest.get("stages", []):
                receipt = row.get("native_report")
                if isinstance(receipt, dict) and receipt.get("path"):
                    queue.append((receipt["path"], receipt.get("sha256"), None))
            for report in sorted(build_path.glob("*.json")):
                if report != manifest_path:
                    queue.append((str(report), sha256(report), None))
    for reference in extra_references:
        if reference:
            queue.append((str(reference), None, None))

    def discover(value, key=None):
        if isinstance(value, dict):
            if key in ("evidence", "native_report", "report") and isinstance(value.get("path"), str):
                queue.append((value["path"], value.get("sha256"), value))
            for child_key, child in value.items():
                discover(child, child_key)
        elif isinstance(value, list):
            for child in value:
                discover(child, key)

    while queue:
        source_value, expected_sha, detail = queue.pop(0)
        if source_value in seen:
            continue
        seen.add(source_value)
        source = Path(source_value)
        record = {"source": source_value, "expected_sha256": expected_sha}
        # Private captured trees are outside the referenced-evidence contract.
        # Exclude them before exists()/is_symlink(), which would otherwise
        # reject (or follow) a private code-tree link.
        if EVIDENCE_EXCLUDED_PARTS.intersection(source.parts):
            record["status"] = "excluded-private-tree"
            path_map[source_value] = record
            continue
        if not source.is_absolute() or not source.exists():
            record["status"] = "missing-at-export"
            path_map[source_value] = record
            continue
        if source.is_symlink():
            raise ValueError("Symlink in referenced evidence: " + source_value)
        if source.is_file() and expected_sha and sha256(source) != expected_sha:
            record["status"] = "source-hash-mismatch"
            record["source_sha256"] = sha256(source)
            path_map[source_value] = record
            continue
        digest_root = hashlib.sha256(source_value.encode("utf-8")).hexdigest()[:20]
        prefix = Path("referenced") / digest_root
        candidates = [source] if source.is_file() else sorted(source.rglob("*"))
        copied = []
        for item in candidates:
            rel = Path(item.name) if source.is_file() else item.relative_to(source)
            if EVIDENCE_EXCLUDED_PARTS.intersection(rel.parts):
                continue
            if item.is_symlink():
                raise ValueError("Symlink in referenced evidence: " + str(item))
            if not item.is_file() or item.suffix.lower() not in EVIDENCE_SUFFIXES:
                continue
            dest_rel = prefix / rel
            dest = target / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(item), str(dest))
            digest = sha256(dest)
            files[dest_rel.as_posix()] = digest
            copied.append({"path": dest_rel.as_posix(), "sha256": digest})
            if item.suffix.lower() == ".json":
                try:
                    discover(read_json(item))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
        record["files"] = copied
        record["status"] = "copied" if copied else "no-allowlisted-files"
        if detail:
            record["claims"] = {key: detail.get(key) for key in ("results_sha256", "identity_sha256", "capture_trace_sha256", "wav_sha256") if detail.get(key)}
        path_map[source_value] = record
    for source_value in (source_identity, artifact_manifest, provisioning_log):
        if not source_value:
            continue
        source = Path(source_value)
        if not source.is_file() or source.is_symlink():
            continue
        rel = Path(source.name)
        dest = target / rel
        if dest.exists():
            continue
        shutil.copyfile(str(source), str(dest))
        files[rel.as_posix()] = sha256(dest)
    index = {"schema_version": 1, "build_directory_present": bool(build_path and build_path.is_dir()),
             "files": files, "source_path_map": path_map}
    index_path = target / "evidence-index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index

def verify_browser_site(site_root, node="node"):
    requested_site = Path(site_root)
    if requested_site.is_symlink():
        raise ValueError("Invalid static site root")
    site = requested_site.resolve(strict=True)
    if not site.is_dir():
        raise ValueError("Invalid static site root")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = "http://127.0.0.1:%d/" % server.server_address[1]
        smoke = Path(__file__).resolve().with_name("manual-site-smoke.cjs")
        subprocess.check_call([node, str(smoke), url], cwd=str(Path(__file__).resolve().parents[2]))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    package = sub.add_parser("package")
    package.add_argument("--repo-root", required=True)
    package.add_argument("--build-evidence", required=True)
    package.add_argument("--source-identity", required=True)
    package.add_argument("--output", required=True)
    package.add_argument("--repository", required=True)
    package.add_argument("--run-id", required=True, type=int)
    package.add_argument("--run-attempt", required=True, type=int)
    package.add_argument("--pr-number", type=int)
    package.add_argument("--pr-head-sha")
    package.add_argument("--pr-base-ref")
    package.add_argument("--verify-browser", action="store_true")
    package.add_argument("--node", default="node")
    evidence = sub.add_parser("evidence-bundle")
    evidence.add_argument("--build-evidence")
    evidence.add_argument("--output", required=True)
    evidence.add_argument("--source-identity")
    evidence.add_argument("--artifact-manifest")
    evidence.add_argument("--provisioning-log")
    evidence.add_argument("--extra-reference", action="append", default=[])
    verify_site = sub.add_parser("verify-site")
    verify_site.add_argument("--site-root", required=True)
    verify_site.add_argument("--node", default="node")
    options = parser.parse_args()
    if options.command == "evidence-bundle":
        result = make_evidence_bundle(options.build_evidence, options.output, options.source_identity,
                                      options.artifact_manifest, options.provisioning_log, options.extra_reference)
        print(json.dumps({"evidence_files": len(result["files"]), "referenced_paths": len(result["source_path_map"])}, sort_keys=True))
        return
    if options.command == "verify-site":
        verify_browser_site(options.site_root, options.node)
        return
    if options.command == "package":
        provenance = dict(repository=options.repository, producer_run_id=options.run_id,
                          producer_run_attempt=options.run_attempt, pr_number=options.pr_number,
                          pr_head_sha=options.pr_head_sha, pr_base_ref=options.pr_base_ref)
        result = make_artifact(options.repo_root, options.build_evidence, options.source_identity,
                               options.output, provenance)
        if options.verify_browser:
            verify_browser_site(Path(options.output) / "manual-site", options.node)
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
