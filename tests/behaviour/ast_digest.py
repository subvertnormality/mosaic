"""Interpreter-independent digest of a Python AST.

ast.dump() differs between CPython releases (3.8 wraps subscripts in Index,
records Constant.kind and prints empty fields; 3.12 adds type_params), so a
pinned ast.dump() hash cannot hold on both the CI interpreter and a local one.
This serialises the same structure with those representation differences
normalised, so equal code gives an equal digest on 3.8 through 3.12.
"""
import ast
import hashlib

_IGNORED_FIELDS = {"kind", "type_comment", "type_params"}


def _canonical(node):
    if isinstance(node, list):
        return "[" + ",".join(_canonical(item) for item in node) + "]"
    if not isinstance(node, ast.AST):
        return repr(node)
    index = getattr(ast, "Index", None)
    if index is not None and type(node) is index:  # Python 3.8 subscript wrapper
        return _canonical(node.value)
    ext_slice = getattr(ast, "ExtSlice", None)
    if ext_slice is not None and type(node) is ext_slice:
        return _canonical(ast.Tuple(elts=node.dims, ctx=ast.Load()))
    fields = []
    for name in node._fields:
        if name in _IGNORED_FIELDS:
            continue
        value = getattr(node, name, None)
        if value is None or value == []:
            continue
        fields.append(name + "=" + _canonical(value))
    return type(node).__name__ + "(" + ",".join(fields) + ")"


def ast_digest(node):
    """SHA-256 of the normalised AST, stable across supported interpreters."""
    return hashlib.sha256(_canonical(node).encode()).hexdigest()
