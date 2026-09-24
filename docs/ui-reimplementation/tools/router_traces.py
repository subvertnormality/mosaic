"""Generate deterministic router traces from the presentation oracle (model.py).

lib/tests/lib/ui_router_tests.lua replays each trace through lib/ui_router.lua
and requires the same rule id, effect list and resulting state, or the same
failure, after every event. Run with --check to fail when the file is stale.
"""
import json, random, sys
from copy import deepcopy
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'tools'))
import model

OUT = R / 'generated' / 'router-traces.json'
SEED, WALKS, LENGTH, SHORT = 1729, 60, 40, 3
STATE_KEYS = ['screen', 'context', 'native', 'modal', 'held', 'shift', 'dirty', 'family',
              'field_kind', 'field_id', 'target', 'return_stack', 'generation']


def doctor_payload(spec, rnd):
    inputs = spec['doctor_routes']['inputs']
    return {k: rnd.choice(inputs[k]['values']) for k in model.DOCTOR_KEYS}


def payload_for(spec, state, event, rnd):
    payload = {}
    if event in ('hold.begin', 'hold.change'):
        payload['steps'] = sorted(rnd.sample(range(1, 65), rnd.randint(1, 3)))
    rows = spec['tasks']['rows'].get(state['screen'])
    if rows and rnd.random() < 0.8:
        payload['task'] = rnd.choice(rows)['id']
    if event == 'grid.outcome':
        flow_id = rnd.choice(sorted(spec['flows']))
        payload['flow_id'] = flow_id
        if spec['flows'][flow_id]['new'].get('routes') == 'doctor_routes':
            payload.update(doctor_payload(spec, rnd))
            payload['outcome'] = rnd.choice(spec['doctor_routes']['flows'][flow_id]['outcomes'])
        if rnd.random() < 0.5:
            payload['target'] = {'channel': rnd.randint(1, 16), 'song_slot': rnd.randint(1, 90), 'step_set': []}
    return payload


def mutate_flags(state, rnd):
    # Presentation flags the router does not own (field kind/id, modal, native) are
    # set by adapters; walks vary them so every guard class is exercised.
    if rnd.random() < 0.3:
        state['field_kind'] = rnd.choice(['value', 'readonly', 'action', 'inspection', 'unavailable'])
    if rnd.random() < 0.1:
        state['modal'] = not state['modal']
    if rnd.random() < 0.05:
        state['native'] = not state['native']
    if rnd.random() < 0.2:
        state['dirty'] = not state['dirty']


def diff(before, after):
    return {k: after[k] for k in STATE_KEYS if before.get(k) != after[k]}


def walk(spec, rnd, edges, state, length, first=None):
    events = spec['input_algebra']['events']
    steps = []
    for index in range(length):
        before = {k: state[k] for k in STATE_KEYS}
        mutate_flags(state, rnd)
        if state['screen'] in edges and rnd.random() < 0.5:
            state['field_id'] = rnd.choice(edges[state['screen']])
        entry = {'set': diff(before, state)}
        event = first if index == 0 and first else rnd.choice(events)
        payload = payload_for(spec, state, event, rnd)
        entry.update(event=event, payload=payload)
        prior = {k: state[k] for k in STATE_KEYS}
        try:
            state, ops, rule = model.step(spec, state, event, payload)
            entry.update(rule=rule, ops=[o['op'] for o in ops], diff=diff(prior, state))
        except (ValueError, KeyError):
            entry['error'] = True
        steps.append(entry)
    return steps


def build():
    spec = json.loads((R / 'spec.json').read_text(encoding='utf8'))
    rnd = random.Random(SEED)
    edges = {}
    for edge in spec['feature_action_edges']:
        edges.setdefault(edge['from'], []).append(edge['field_id'])
    walks = []
    # Every screen in every context it belongs to, then long walks from each primary.
    for sid in sorted(spec['screens']):
        for context in model.contexts(spec, sid):
            # Each event first, from a start whose flags vary, so every rule is reached.
            for event in spec['input_algebra']['events']:
                plain = model.initial(sid, context)
                walks.append({'start': deepcopy(plain), 'steps': walk(spec, rnd, edges, plain, 1, event)})
                start = model.initial(sid, context)
                start['shift'] = rnd.random() < 0.3
                start['held'] = rnd.random() < 0.2
                walks.append({'start': deepcopy(start), 'steps': walk(spec, rnd, edges, start, SHORT, event)})
    for _ in range(WALKS):
        context = rnd.choice(sorted(spec['contexts']))
        start = model.initial(spec['contexts'][context], context)
        walks.append({'start': deepcopy(start), 'steps': walk(spec, rnd, edges, start, LENGTH)})
    return json.dumps({'seed': SEED, 'walks': walks}, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'


if __name__ == '__main__':
    text = build()
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding='utf8') != text:
            sys.exit('router-traces.json is stale; run tools/router_traces.py')
        print('router traces current')
    else:
        OUT.write_text(text, encoding='utf8')
        data = json.loads(text)
        steps = [e for w in data['walks'] for e in w['steps']]
        total, errors = len(steps), sum(1 for e in steps if e.get('error'))
        rules = {e['rule'] for e in steps if 'rule' in e}
        print('wrote', total, 'steps,', errors, 'errors,', len(rules), 'rules covered')
