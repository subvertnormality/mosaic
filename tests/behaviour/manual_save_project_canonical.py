"""Complete stock decoded-content equality; no field/value normalization."""
from pathlib import Path
import hashlib,json,subprocess,os
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def runtime_command(fixture, runtime, *args):
    """Run the pinned Lua with its exact bundled loader and shared objects."""
    fixture=Path(fixture).resolve()
    def pinned(record, label):
        relative=Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Changed invoked Lua runtime identity: nonportable {label} path")
        resolved=(fixture/relative).resolve()
        if fixture not in resolved.parents or not resolved.is_file():
            raise ValueError(f"Changed invoked Lua runtime identity: missing {label}")
        if digest(resolved)!=record["sha256"]:
            raise ValueError(f"Changed invoked Lua runtime identity: {label} digest")
        return resolved
    manifest=json.loads((fixture/"CANONICAL-RUNTIME.json").read_text())
    binary=pinned(manifest["binary"],"binary")
    loader=pinned(manifest["loader"],"loader")
    libraries=[pinned(item,"library") for item in manifest["libraries"]]
    library_path=Path(manifest["library_path"])
    if library_path.is_absolute() or ".." in library_path.parts:
        raise ValueError("Changed invoked Lua runtime identity: nonportable library path")
    library_dir=(fixture/library_path).resolve()
    if fixture not in library_dir.parents or any(lib.parent!=library_dir for lib in libraries):
        raise ValueError("Changed invoked Lua runtime identity: changed library directory")
    tab=fixture/manifest["tabutil"]["relative"]
    if digest(tab)!=manifest["tabutil"]["sha256"]:
        raise ValueError("Changed invoked cached tabutil source")
    # Source-cache files are byte snapshots and intentionally do not retain mode bits.
    # The pinned loader's digest is checked above before making its copy executable.
    os.chmod(loader,loader.stat().st_mode|0o111)
    return [str(loader),"--inhibit-cache","--library-path",str(library_dir),str(binary),*map(str,args)]

def canonical(path, fixture, oracle):
    fixture=Path(fixture);oracle=Path(oracle)
    if digest(oracle)!="1704dd05df57a472b3351abd0e01a8361d9d2538df988bc64668792de5fe32f7":raise ValueError("Changed stock decoded-content oracle")
    runtime=json.loads((fixture/"CANONICAL-RUNTIME.json").read_text())
    command=runtime_command(fixture,runtime,str(oracle),str(fixture/"canonical-runtime"),str(path))
    return subprocess.check_output(command)
def prove(saved, original, fixture, oracle):
    before=canonical(original,fixture,oracle);after=canonical(saved,fixture,oracle)
    if before!=after:raise ValueError('Changed complete decoded project content')
    return dict(original_byte_sha256=digest(original),observed_byte_sha256=digest(saved),decoded_sha256=hashlib.sha256(before).hexdigest(),decoded_bytes=len(before),oracle_sha256=digest(oracle),runtime_manifest_sha256=digest(Path(fixture)/'CANONICAL-RUNTIME.json'))
