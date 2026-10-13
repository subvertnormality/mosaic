"""Versioned digest for explicitly declared interval transition contracts."""
import hashlib
import json


def native_transition_hash_v8(native):
    if not isinstance(native, dict) or native.get("contract_schema") != "mosaic-native-transition-v3" or native.get("transition_scope") != "interval":
        raise ValueError("v8 digests require an explicit mosaic-native-transition-v3 interval")
    raw = json.dumps(native, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def native_transition_hash_prelude(native):
    if not isinstance(native, dict) or native.get("contract_schema") != "mosaic-native-transition-v4" or native.get("transition_scope") != "prelude":
        raise ValueError("prelude digests require an explicit captured mosaic-native-transition-v4 prelude")
    raw=json.dumps(native,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
