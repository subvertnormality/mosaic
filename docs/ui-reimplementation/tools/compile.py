"""Compile all native specimens and data-bound screens into Lua replay inputs."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def lua(x):
 if x is None:return 'nil'
 if x is True:return 'true'
 if x is False:return 'false'
 if isinstance(x,(int,float)):return str(x)
 if isinstance(x,str):return json.dumps(x,ensure_ascii=False)
 if isinstance(x,list):return '{'+','.join(lua(v)for v in x)+'}'
 return '{'+','.join('['+lua(k)+']='+lua(v)for k,v in x.items())+'}'
s=json.loads((R/'spec.json').read_text(encoding='utf8'));fixtures=json.loads((R/'fixtures.json').read_text(encoding='utf8'));cases=[]
for fid,f in fixtures.items():
 screen=s['screens'][f['screen']];cases.append({'id':'accepted.'+fid,'program':screen['render']['program'],'model':f,'field':f['field']})
 v={'screen':f['screen'],'title':f['title'],'scope':f['context'],'fields':[{'id':str(n),'label':a,'short_label':a,'value':b,'compact_value':b,'kind':'readonly'}for n,(a,b)in enumerate(f['rows'])],'selected':f['field']+1,'layout':screen['live_render']['layout'],'footer':'SPECIMEN / NOT LIVE','status':f.get('badge',''),'art':screen['live_render']['art']}
 if v['layout']=='pattern64':v['cells']=[{'level':2,'selected':k==f['field'],'playing':False}for k in range(64)]
 cases.append({'id':'bound.'+fid,'program':'screen','model':v})
 # Boundary fixture uses empty providers; must not crash or mutate.
for sid,x in s['screens'].items():
 v={'screen':sid,'title':x['title'],'scope':'NO TARGET','fields':[],'selected':1,'layout':'focused','footer':'EMPTY','status':''}
 cases.append({'id':'empty.'+sid,'program':'screen','model':v})
(R/'generated/replay-input.lua').write_text('return '+lua(cases)+'\n',encoding='utf8')
print('Compiled',len(cases),'Lua replay cases')
