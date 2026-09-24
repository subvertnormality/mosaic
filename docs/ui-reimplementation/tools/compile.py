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
# Maximum numeric domains on every screen at its declared layout/art, each field selected in turn.
# 16383: NRPN/14-bit (lib/devices/nrpn_codec.lua); 65535: merge seed (lib/musical_merge/config.lua);
# -8192: signed 14-bit edge; negative fractional fine start (lib/rhythm_doctor/ui_adapter.lua FINE START, tostring ms).
MAX=[('NRPN VALUE','NRPN','16383'),('MERGE SEED','SEED','65535'),('SIGNED 14 BIT','BEND','-8192'),('FINE START','FINE','-2999.9773242630ms'),('OFF SENTINEL','OFF','OFF'),('ZERO','ZERO','0')]
for sid,x in s['screens'].items():
 lay=x['live_render']['layout'];n=len(MAX)
 for sel in range(1,n+1):
  v={'screen':sid,'title':x['title'],'scope':'MAX NUMERIC','fields':[{'id':'max'+str(k),'label':a,'short_label':b,'value':c,'compact_value':c,'kind':'value'}for k,(a,b,c)in enumerate(MAX)],'selected':sel,'layout':lay,'footer':'E1 FIELD E3 VALUE','status':'','art':x['live_render']['art']}
  if lay=='pattern64':v['cells']=[{'level':2,'selected':k==0,'playing':False}for k in range(64)]
  cases.append({'id':'max.'+sid+'.'+str(sel),'program':'screen','model':v,'check_values':lay!='pattern64'})
# A numeric value wider than 126px must fail visibly (flag + LAYOUT OVERFLOW), never clip or raise.
for lay in ['focused','detail','overview_masks','overview_params']:
 v={'screen':'overflow','title':'OVERFLOW','scope':'X','fields':[{'id':'wide','label':'WIDE','short_label':'W','value':'9'*40,'compact_value':'9'*40,'kind':'value'}],'selected':1,'layout':lay,'footer':'','status':''}
 cases.append({'id':'overflow.'+lay,'program':'screen','model':v,'expect_overflow':True})
(R/'generated/replay-input.lua').write_text('return '+lua(cases)+'\n',encoding='utf8')
print('Compiled',len(cases),'Lua replay cases')
