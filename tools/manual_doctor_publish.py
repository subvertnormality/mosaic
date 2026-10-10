"""Audit immutable Manual/Auto Doctor runs; publish only with explicit --publish."""
import argparse, copy, hashlib, json
from pathlib import Path
import yaml,jsonschema
from manual_publication_verify import audit_doctor
ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def collect_reports(manual_report,auto_report):
    reports=[];runs=[]
    for path,wanted in ((manual_report,'doctor-scene.yaml'),(auto_report,'doctor-auto-probe.yaml')):
        path=Path(path).resolve()
        if path.name!='report.json':raise ValueError('Requires original immutable report.json')
        value=json.loads(path.read_text())
        if Path(value['source']['yaml_path']).name!=wanted:raise ValueError('Doctor modes must be Manual then Auto')
        reports.append(value);runs.append(dict(report=str(path),report_sha256=digest(path)))
    if reports[0]['controlled_time']!=reports[1]['controlled_time']:raise ValueError('Changed audio lane applicability')
    return dict(publication_kind='doctor-native-audio',schema_version=1,passed=True,
        clock_mode='real-time',complete_regression_run=False,hardware_timing_equivalent=False,
        controlled_time=copy.deepcopy(reports[0]['controlled_time']),evidence=dict(runs=runs),
        scenes=[copy.deepcopy(scene) for report in reports for scene in report['scenes']])
def authored_bindings(document):
    scenes=[]
    for scene in document['scenes']:
        row=copy.deepcopy(scene)
        row['feature_id']='rhythm-doctor';row['profile']='audio-real-time'
        for step in row['steps']:step.pop('output',None)
        scenes.append(row)
    return dict(schema_version=1,fixture_kind='doctor-native-audio',
        dataset='generated/doctor-scenes.json',source_paths=['doctor-scene.yaml','doctor-auto-probe.yaml'],scenes=scenes)
def atomic_text(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.new');temporary.write_text(value);temporary.replace(path)
def publish_reports(manual_report,auto_report,manual_root=None,publish=False):
    document=collect_reports(manual_report,auto_report)
    audit=audit_doctor(document) # All native/source/semantic/PCM checks precede any write.
    if audit.get('passed') is not True:raise ValueError('Independent Doctor audit did not pass')
    if publish:
        destination=Path(manual_root) if manual_root else ROOT/'manual'
        bindings=authored_bindings(document)
        schema=json.loads((ROOT/'manual/doctor-bindings.schema.json').read_text())
        jsonschema.Draft7Validator(schema).validate(bindings)
        atomic_text(destination/'generated/doctor-scenes.json',json.dumps(document,separators=(',',':'))+'\n')
        atomic_text(destination/'features/scenes-doctor-scenes.yaml',yaml.safe_dump(bindings,sort_keys=False,allow_unicode=True))
    return dict(document=document,audit=audit,published=publish)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manual-report',type=Path,required=True)
    parser.add_argument('--auto-report',type=Path,required=True)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args();result=publish_reports(args.manual_report,args.auto_report,publish=args.publish)
    print(json.dumps(dict(passed=True,published=result['published'],scenes=len(result['document']['scenes']),frames=sum(len(scene['steps']) for scene in result['document']['scenes']))))
if __name__=='__main__':main()
