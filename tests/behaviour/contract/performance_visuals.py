"""Characterisation of exact exported frame/grid performance observations.

These whole-image oracles are UI contracts under the migration plan's catch-all;
their function bodies are unchanged from the standalone performance runners.
"""
import base64
import hashlib


def render_observation(value):
    state=value['state'];pixels=base64.b64decode(state['frame']['pixels_base64'],validate=True);grid=state['grid']
    assert len(pixels)==128*64*4,('Frame shape',len(pixels))
    assert len(grid)==128 and all(type(x) is int and 0<=x<=15 for x in grid),('Grid shape',len(grid))
    assert hashlib.sha256(pixels).hexdigest()==state['frame']['sha256'],'Frame hash mismatch'
    return dict(frame_revision=value['frame_revision'],grid_revision=value['grid_revision'],
      frame_sha256=state['frame']['sha256'],grid_sha256=hashlib.sha256(bytes(grid)).hexdigest())


def assert_visual_recovery(before, changed):
    """A physical page input after overload must visibly reach grid and screen."""
    assert changed['grid_revision'] > before['grid_revision'], 'grid revision did not advance'
    assert changed['frame_revision'] > before['frame_revision'], 'frame revision did not advance'
    assert changed['state']['grid'] != before['state']['grid'], 'grid image did not change'
    assert changed['state']['frame']['sha256'] != before['state']['frame']['sha256'], \
        'screen image did not change'
    return dict(grid_revisions=[before['grid_revision'], changed['grid_revision']],
                frame_revisions=[before['frame_revision'], changed['frame_revision']],
                frame_hashes=[before['state']['frame']['sha256'],
                              changed['state']['frame']['sha256']])
