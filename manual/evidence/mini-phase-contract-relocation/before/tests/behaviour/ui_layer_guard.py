"""Static fail-closed guard and contract classifier for the UI migration."""

import ast
import importlib
import inspect
import json
from functools import lru_cache
from pathlib import Path


BEHAVIOUR = Path(__file__).resolve().parent
EXEMPT = {
    "driver.py", "ui.py", "frame_oracle.py", "ui_layer_guard.py",
    "run.py", "repeat.py", "suite.py", "ui_migration_gate.py",
}
RAW_METHODS = {"tap", "key", "enc", "hold_tap", "led_values", "screen_header"}
RAW_STATE_KEYS = {"grid", "frame"}
CONTRACT_STATE_KEYS = {"grid", "frame", "pixels_base64"}
REACHABILITY_EXEMPT_MODULES = {
    "driver", "ui", "frame_oracle", "run", "repeat", "suite",
    "ui_layer_guard", "ui_migration_gate",
}


def _literal(value):
    if isinstance(value, ast.Index):
        value = value.value
    return value.value if isinstance(value, ast.Constant) else None


@lru_cache(maxsize=None)
def _tree(path):
    path = Path(path)
    return ast.parse(path.read_text(), filename=str(path))


def _raw_sites_in_node(node, include_frame_imports=False):
    sites = []
    for item in ast.walk(node):
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute):
            if item.func.attr in RAW_METHODS:
                sites.append((item.lineno, item.func.attr))
            elif item.func.attr == "action":
                kinds = [_literal(keyword.value) for keyword in item.keywords if keyword.arg == "type"]
                if any(kind in {"grid", "key", "enc"} for kind in kinds):
                    sites.append((item.lineno, "action:" + kinds[0]))
        elif isinstance(item, ast.Subscript) and _literal(item.slice) in RAW_STATE_KEYS:
            sites.append((item.lineno, "state:" + _literal(item.slice)))
        elif include_frame_imports and isinstance(item, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in item.names]
            if getattr(item, "module", None) == "frame_oracle" or "frame_oracle" in names:
                sites.append((item.lineno, "frame_oracle"))
    return sorted(set(sites))


def raw_sites(path):
    tree = _tree(str(Path(path).resolve()))
    return _raw_sites_in_node(tree, include_frame_imports=True)


def case_modules():
    return [path for path in BEHAVIOUR.glob("*.py")
            if path.name not in EXEMPT and not path.name.startswith("test_")]


def validate_ui_layer():
    """Reject raw UI in ordinary case modules or reachable non-contract code."""
    errors = []
    for path in case_modules():
        sites = raw_sites(path)
        if sites:
            errors.append("raw UI outside contract module: %s:%s" %
                          (path.name, sites[0][0]))

    from cases import CASES
    contract = classify_contract_cases(CASES)
    for case_id, case in CASES.items():
        if case_id in contract:
            continue
        owner = _source_path(case["run"])
        if owner is None:
            continue
        dependencies = callable_raw_dependencies(case["run"])
        if dependencies:
            dependency, line, kind = dependencies[0]
            errors.append(
                "migrated case reaches raw UI: %s -> %s:%s (%s)"
                % (case_id, dependency, line, kind)
            )
    return errors


def _source_path(function):
    try:
        path = Path(inspect.getsourcefile(function)).resolve()
        path.relative_to(BEHAVIOUR)
        return path
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=None)
def _callable_node(path, name, first_line):
    candidates = []
    for node in ast.walk(_tree(path)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            candidates.append(node)
        elif name == "<lambda>" and isinstance(node, ast.Lambda):
            candidates.append(node)
    exact = [node for node in candidates if node.lineno == first_line]
    if exact:
        return exact[0]
    before = [node for node in candidates if node.lineno >= first_line]
    return min(before or candidates, key=lambda node: abs(node.lineno - first_line), default=None)


def _qualified(function):
    return "%s.%s" % (function.__module__, function.__name__)


@lru_cache(maxsize=1)
def _verb_sources():
    return set(json.loads((BEHAVIOUR / "ui_verb_sources.json").read_text()))


def _has_custom_oracle(function, node):
    if _qualified(function) in _verb_sources():
        return False
    for item in ast.walk(node):
        if isinstance(item, ast.Subscript) and _literal(item.slice) in CONTRACT_STATE_KEYS:
            return True
        if isinstance(item, ast.Call):
            if isinstance(item.func, ast.Name) and item.func.id == "render":
                return True
            if isinstance(item.func, ast.Attribute) and item.func.attr == "render":
                return True
    return False


def _imported_functions(node):
    values = {}
    modules = {}
    for item in ast.walk(node):
        if isinstance(item, ast.ImportFrom) and item.module:
            try:
                module = importlib.import_module(item.module)
            except (ImportError, OSError):
                continue
            for alias in item.names:
                value = getattr(module, alias.name, None)
                values[alias.asname or alias.name] = value
        elif isinstance(item, ast.Import):
            for alias in item.names:
                try:
                    modules[alias.asname or alias.name.split(".")[0]] = importlib.import_module(alias.name)
                except (ImportError, OSError):
                    continue
    return values, modules


def _reachable_functions(function, node):
    imported, imported_modules = _imported_functions(node)
    found = []
    for item in ast.walk(node):
        if not isinstance(item, ast.Call):
            continue
        value = None
        if isinstance(item.func, ast.Name):
            value = imported.get(item.func.id, function.__globals__.get(item.func.id))
        elif isinstance(item.func, ast.Attribute) and isinstance(item.func.value, ast.Name):
            base = imported_modules.get(item.func.value.id, function.__globals__.get(item.func.value.id))
            value = getattr(base, item.func.attr, None) if base is not None else None
        if inspect.isfunction(value) and _source_path(value) is not None:
            found.append(value)
    return found


def callable_raw_dependencies(function):
    """Return raw UI sites reachable from a case/helper, excluding layer internals."""
    pending = [function]
    visited = set()
    found = []
    while pending:
        current = pending.pop()
        identity = (current.__module__, current.__name__, current.__code__.co_firstlineno)
        if identity in visited:
            continue
        visited.add(identity)
        if current.__module__ in {"driver", "ui"}:
            continue
        path = _source_path(current)
        if path is None:
            continue
        node = _callable_node(str(path), current.__name__, current.__code__.co_firstlineno)
        if node is None:
            raise AssertionError("cannot locate source node for %r" % (identity,))
        if current.__module__ == "frame_oracle":
            found.append((_qualified(current), node.lineno, "frame_oracle"))
            continue
        for line, kind in _raw_sites_in_node(node):
            found.append((_qualified(current), line, kind))
        pending.extend(_reachable_functions(current, node))
    return sorted(set(found))


def callable_is_contract(function):
    pending = [function]
    visited = set()
    while pending:
        current = pending.pop()
        identity = (current.__module__, current.__name__, current.__code__.co_firstlineno)
        if identity in visited:
            continue
        visited.add(identity)
        if current.__module__.startswith("contract."):
            return True
        if current.__module__ in REACHABILITY_EXEMPT_MODULES:
            continue
        path = _source_path(current)
        if path is None:
            continue
        node = _callable_node(str(path), current.__name__, current.__code__.co_firstlineno)
        if node is None:
            raise AssertionError("cannot locate source node for %r" % (identity,))
        if _has_custom_oracle(current, node):
            return True
        pending.extend(_reachable_functions(current, node))
    return False


def load_baseline_failures():
    path = BEHAVIOUR / "contract_baseline_failures.json"
    value = json.loads(path.read_text())
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssertionError("contract_baseline_failures.json must be a string list")
    if len(value) != len(set(value)):
        raise AssertionError("duplicate contract baseline failures")
    return set(value)


def load_gate_failures():
    path = BEHAVIOUR / "contract_gate_failures.json"
    value = json.loads(path.read_text())
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssertionError("contract_gate_failures.json must be a string list")
    if len(value) != len(set(value)):
        raise AssertionError("duplicate contract gate failures")
    return set(value)


def classify_contract_cases(cases=None):
    if cases is None:
        from cases import CASES
        cases = CASES
    contract = set(load_baseline_failures()) | load_gate_failures()
    for case_id, case in cases.items():
        if any(requirement.startswith("NAV-") for requirement in case.get("requirements", [])):
            contract.add(case_id)
        elif callable_is_contract(case["run"]):
            contract.add(case_id)
    unknown = contract - set(cases)
    if unknown:
        raise AssertionError("unknown contract cases: " + ", ".join(sorted(unknown)))
    return contract
