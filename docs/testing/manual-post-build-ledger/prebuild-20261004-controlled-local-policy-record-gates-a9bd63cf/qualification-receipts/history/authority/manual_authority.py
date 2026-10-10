"""Resolve stable manual citations without rewriting historical README evidence.

Authoring identity is separate from manual_sha256: old manifests keep the hash
of the manual actually used, while new runs record all current YAML sources.
No helper claims full behaviour campaign coverage.
"""
import hashlib,json,importlib.util
from pathlib import Path
import yaml

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def authoring_identity(root):
    root=Path(root).resolve()
    config_path=root/"manual/book.yaml"
    if not config_path.is_file():raise ValueError("Missing authoring: manual/book.yaml")
    config=yaml.safe_load(config_path.read_text())
    paths={"manual/book.yaml"}
    configured = [source for key in ("sources","scene_sources","audio_sources","schema_sources") for source in config.get(key,[])]
    if config.get("course_source"):
        configured.append(config["course_source"])
    for source in configured:
        path=(root/"manual"/source).resolve()
        if root not in path.parents:raise ValueError("Unsafe authoring path: "+source)
        if not path.is_file():raise ValueError("Missing authoring: "+source)
        paths.add(path.relative_to(root).as_posix())
    # An unlisted YAML authoring file is a stale index, not silently ignored.
    actual={p.relative_to(root).as_posix() for p in (root/"manual/features").glob("*.yaml")}
    if actual-paths:raise ValueError("Unlisted authoring: "+",".join(sorted(actual-paths)))
    files={path:sha(root/path) for path in sorted(paths)}
    digest=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"sha256":digest,"files":files}

def resolve_feature(book,citation):
    identifier=citation
    if identifier.startswith("manual:"):identifier=identifier[len("manual:"):]
    if "#" in identifier:identifier=identifier.rsplit("#",1)[1]
    aliases=book.get("aliases",{})
    seen=set()
    while identifier in aliases:
        if identifier in seen:raise ValueError("Cyclic manual alias: "+identifier)
        seen.add(identifier);identifier=aliases[identifier]
    found=[f for f in book["features"] if f["id"]==identifier]
    if len(found)!=1:raise ValueError("Unknown manual feature: "+identifier)
    return found[0]

def feature_links(inventory,features,section_ids):
    """Return additive mappings; never rewrite requirements, cases or baselines."""
    known={f["id"] for f in features}
    result={}
    for section in inventory["sections"]:
        if section["id"] in section_ids:
            fid=section_ids[section["id"]]
            if fid not in known:raise ValueError("Unknown manual feature: "+fid)
            result[section["id"]]=[fid]
    return result

def load_compiled(root):
    path=Path(root)/"manual/generated/book.json"
    if not path.is_file():raise ValueError("Missing compiled manual")
    return json.loads(path.read_text())

def verify_authority(root,inventory,book=None):
    """Fail closed when migration mappings or authored scene contracts are stale."""
    authority=inventory.get("manual_authority")
    if not authority or authority.get("status") in ("inactive","prepared"):return None  # Original README gate remains authoritative.
    identity=authoring_identity(root)
    if identity!=authority["identity"]:raise ValueError("Manual authoring changed: reconcile inventory")
    if book is None:
        book=load_compiled(root)
        module=compiler_module(root)
        authored=module.load()
        current=hashlib.sha256(json.dumps(authored,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if book.get("source_sha256")!=current:
            raise ValueError("Compiled manual source changed: regenerate manual")
        for key in ("features","aliases","navigation","title","edition","learning_path","project","course_title","course_summary"):
            if book.get(key)!=authored.get(key):raise ValueError("Compiled manual contents changed: "+key)

    # Bind compiled contents to YAML when available; JSON alone cannot bless edits.
    if book.get("authoring_identity")!=identity:
        raise ValueError("Compiled manual authoring changed: regenerate manual")
    if authority.get("status")=="active":
        if book.get("complete_manual") is not True or any(f.get("review",{}).get("status") not in ("verified","pilot-reviewed") for f in book["features"]):
            raise ValueError("Manual content migration incomplete")
    links=authority.get("feature_links",{})
    for section in inventory["sections"]:
        if section["id"].startswith("MAN-") and section.get("status")!="absent-from-current-manual":
            if not links.get(section["id"]):raise ValueError("Missing feature link: "+section["id"])
    for section,identifiers in links.items():
        if section not in {s["id"] for s in inventory["sections"]}:raise ValueError("Unknown section: "+section)
        for identifier in identifiers:
            feature=resolve_feature(book,identifier)
            for scene in feature.get("scene_refs",[]):
                contract=book.get("scenes",{}).get(scene)
                if not contract or not contract.get("behaviour_case") or not contract.get("steps"):
                    raise ValueError("Missing scene contract: "+scene)
                for step in contract["steps"]:
                    binding=step.get("output",{}).get("binding",{})
                    if (binding.get("passed") is not True or not binding.get("semantic_assertions")
                            or not binding.get("sha256") or not binding.get("grid_sha256")):
                        raise ValueError("Missing semantic scene binding: "+scene)
    if authority.get("status")=="active":
        compiler=compiler_module(root)
        if not hasattr(compiler,"compile_book"):raise ValueError("Missing complete manual compiler")
        expected=compiler.compile_book(compiler.load())
        if expected.get("complete_manual") is not True:raise ValueError("Manual content migration incomplete")
        if expected!=book:raise ValueError("Compiled manual generated contracts changed")
    return identity

def source_path(root,inventory,source):
    """Resolve a source revision explicitly; aliases never rewrite historical records."""
    path=source['path']
    alias=inventory.get('manual_source_aliases',{}).get(path)
    if alias:
        path=alias['path']
    elif inventory.get('historical_manual') and path=='README.md':
        path=inventory['historical_manual']['path']
    target=(Path(root)/path).resolve()
    if Path(root).resolve() not in target.parents:raise ValueError('Unsafe manual source: '+path)
    return target

def verify_manual_sources(root,inventory):
    root=Path(root)
    if sha(root/inventory['manual'])!=inventory['manual_sha256']:
        raise ValueError('Manual changed: reconcile inventory')
    for entry in inventory.get('manual_sources',[]):
        if 'path' in entry and sha(source_path(root,inventory,entry))!=entry['sha256']:
            raise ValueError('Manual source changed: '+entry['path'])
    for key in ('original_manual','historical_manual','section_manual'):
        item=inventory.get(key)
        if item and sha(source_path(root,{},item))!=item['sha256']:
            raise ValueError('Frozen manual source changed: '+item['path'])
    for alias in inventory.get('manual_source_aliases',{}).values():
        if sha(source_path(root,{},alias))!=alias['sha256']:
            raise ValueError('Frozen manual alias changed: '+alias['path'])
    return True

def compiler_module(root):
    compiler=Path(root)/'tools/manual_book.py'
    if not compiler.is_file():raise ValueError('Missing manual compiler')
    spec=importlib.util.spec_from_file_location('manual_authority_compiler',compiler)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def load_authored(root):
    return compiler_module(root).load()

