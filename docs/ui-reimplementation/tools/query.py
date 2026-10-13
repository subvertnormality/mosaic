"""Small, deterministic context bundles for an implementation executor."""
import argparse,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('kind',choices=['screen','flow','manual','slice','summary']);p.add_argument('id',nargs='?');a=p.parse_args()
s=json.loads((R/'spec.json').read_text(encoding='utf8'));i=json.loads((R/'source-inventory.json').read_text(encoding='utf8'))
if a.kind=='screen':
 x=s['screens'][a.id];result={'screen':x,'provider':s['providers'][x['provider']],'field_contract':s['field_contracts'].get(x['provider']),'inputs':[r for r in s['input_algebra']['rules']if ('profile'not in r['when']or x['profile']in ([r['when']['profile']]if isinstance(r['when']['profile'],str)else r['when']['profile']))and('screen'not in r['when']or a.id in ([r['when']['screen']]if isinstance(r['when']['screen'],str)else r['when']['screen']))],'action_edges':[e for e in s['feature_action_edges']if e['from']==a.id or e['to']==a.id],'manual':[{'id':m['id'],'heading':m['heading']}for m in i['manual_sections']if a.id in m['screens']],'acceptance':[c for c in s['acceptance_matrix']if a.id in c['screens']]}
elif a.kind=='flow':result={'flow':s['flows'][a.id],'source_callbacks':[g for g in i['grid_registrations']if a.id in g['replacement_flows']]}
elif a.kind=='manual':result=next(m for m in i['manual_sections']if m['id']==a.id)
elif a.kind=='slice':result=next(m for m in s['migration']if m['id']==a.id)
else:result={'authority':s['authority'],'contexts':s['contexts'],'screens':{k:{'title':v['title'],'provider':v['provider'],'source_route':v['existing_route']}for k,v in s['screens'].items()},'slices':s['migration']}
print(json.dumps(result,ensure_ascii=False,indent=2))
