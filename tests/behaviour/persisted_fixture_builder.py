"""Freeze a saved project made by the checked-out Mosaic as a regression fixture.

usage: MONOME_EMULATOR=... python3 persisted_fixture_builder.py LABEL OUTPUT_ROOT --experimental-install PATH
Builds the project through native gestures (persisted_fixture.build_fixture_project),
autosaves it when idle, cold-restarts from the saved data and records the golden
stream that this Mosaic version plays after reload. Writes OUTPUT_ROOT/LABEL/{data,golden.json}.
"""
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
from driver import Driver, REPO
from persisted_fixture import build_fixture_project, capture_stream

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('label'); parser.add_argument('output_root'); parser.add_argument('--experimental-install', required=True)
    args = parser.parse_args()
    target = Path(args.output_root)/args.label
    assert not target.exists(), 'Fixture already exists: %s' % target
    work = Path(tempfile.mkdtemp(prefix='fixture-'))
    options = dict(clock_mode='controlled-experimental', experimental_install=args.experimental_install)
    (work/'build').mkdir()
    c = Driver(work/'build', **options)
    build_fixture_project(c)
    before = capture_stream(c)
    marks = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob('autosave.*')}
    for _ in range(3): c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and (c.data_directory/n).stat().st_mtime_ns != marks.get(n)
                         for n in ('autosave.ptn', 'autosave.pset')))
    c.finish()
    (work/'reload').mkdir()
    d = Driver(work/'reload', project_seed=c.data_directory, **options)
    d.tap(3, 8); golden = capture_stream(d); d.finish()
    assert [e['bytes'] for e in golden if e['bytes'][0] == 144] == [e['bytes'] for e in before if e['bytes'][0] == 144], \
        'The saving version does not replay its own save identically'
    target.mkdir(parents=True)
    shutil.copytree(c.data_directory, target/'data')
    revision = subprocess.check_output(['git', 'describe', '--tags', '--always', '--dirty'], cwd=REPO, text=True).strip()
    (target/'golden.json').write_text(json.dumps(dict(saved_by=revision, clock_mode='controlled-experimental',
        onsets=17, stream=golden), indent=1) + '\n')
    print(json.dumps(dict(label=args.label, saved_by=revision, events=len(golden), target=str(target))))

if __name__ == '__main__':
    main()
