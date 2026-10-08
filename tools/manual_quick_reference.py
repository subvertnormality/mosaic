"""Generate the public control sheet from the Mosaic manual."""
import argparse,html,importlib.util,os,re
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("quick_reference_book",ROOT/"tools/manual_book.py")
book=importlib.util.module_from_spec(spec);spec.loader.exec_module(book)
escape=html.escape

STYLE="""*{box-sizing:border-box}html{color-scheme:light dark;scroll-behavior:smooth}body{--paper:#f2f0e8;--ink:#202520;--line:#a6aaa0;--signal:#285c40;background:var(--paper);color:var(--ink);margin:0;font:15px/1.5 system-ui,sans-serif}a{color:var(--signal);text-underline-offset:3px}main,header{max-width:1300px;margin:auto;padding:24px}header{border-bottom:1px solid var(--line)}.mast{display:flex;align-items:center;gap:12px}h1{font:700 clamp(30px,7vw,56px)/1 ui-monospace,monospace;letter-spacing:-.08em;margin:0}.mark{display:grid;grid-template-columns:repeat(2,12px);gap:3px}.mark i{width:12px;height:12px;background:var(--signal)}.mark i:nth-child(2){opacity:.65}.mark i:nth-child(3){opacity:.4}.eyebrow,h2{font-family:ui-monospace,monospace}.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:12px}nav{display:flex;flex-wrap:wrap;gap:8px 20px}.search{margin:20px 0;display:flex;align-items:center;gap:12px;flex-wrap:wrap}input,button{font:inherit;border:1px solid var(--line);background:var(--paper);color:var(--ink);padding:8px}input{flex:1;min-width:160px}button{cursor:pointer}.catalogue{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;align-items:start}article{overflow-wrap:anywhere;border:1px solid var(--line);padding:16px;min-width:0;scroll-margin:20px}article h2{font-size:18px;margin:0 0 6px}article p{font-size:13px;margin:8px 0 12px}table{border-collapse:collapse;width:100%;font-size:13px;table-layout:fixed}th,td{padding:8px 6px;border-top:1px solid var(--line);text-align:left;vertical-align:top;overflow-wrap:anywhere}th:first-child,td:first-child{width:52%}td:first-child{font-family:ui-monospace,monospace}th{font-size:11px;text-transform:uppercase;letter-spacing:.05em}.skip{position:absolute;top:-100px;left:12px;padding:12px;background:var(--paper);z-index:10}.skip:focus{top:12px}:focus-visible{outline:3px solid var(--signal);outline-offset:3px}[hidden]{display:none!important}footer{padding:24px 0;border-top:1px solid var(--line);margin-top:24px;font-size:13px}body[data-theme=dark]{--paper:#101510;--ink:#e5eadf;--line:#627361;--signal:#b8dc9c}body[data-theme=light]{color-scheme:light}@media(prefers-color-scheme:dark){body:not([data-theme=light]){--paper:#101510;--ink:#e5eadf;--line:#627361;--signal:#b8dc9c}}@media(max-width:700px){.catalogue{grid-template-columns:1fr}main,header{padding:16px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{header nav,.search,.skip{display:none}.catalogue{gap:10px}article{break-inside:avoid}body{font-size:11px;color:black;background:white}a{color:black}main,header{padding:8px}}"""
SCRIPT="""const find=document.querySelector('#find'), count=document.querySelector('#count'), cards=[...document.querySelectorAll('article')];function filter(){const words=find.value.trim().toLowerCase().split(/\\s+/).filter(Boolean);let visible=0;cards.forEach(card=>{card.hidden=!words.every(word=>card.textContent.toLowerCase().includes(word));visible+=!card.hidden});count.textContent=visible+' of '+cards.length+' features'}find.addEventListener('input',filter);document.querySelector('#clear').addEventListener('click',()=>{find.value='';filter();find.focus()});document.addEventListener('keydown',event=>{if(event.key==='/'&&event.target.tagName!=='INPUT'){event.preventDefault();find.focus()}if(event.key==='Escape'&&event.target===find){find.value='';filter()}});document.querySelector('#theme').addEventListener('click',()=>{const dark=document.body.dataset.theme?document.body.dataset.theme==='dark':matchMedia('(prefers-color-scheme:dark)').matches;document.body.dataset.theme=dark?'light':'dark'});filter();"""

def legacy_rows(path):
    """Extract every leaf gesture/behaviour row from the exact historical sheet."""
    class Rows(HTMLParser):
        def __init__(self):super().__init__();self.stack=[];self.rows=[]
        def handle_starttag(self,tag,attrs):
            classes=dict(attrs).get("class","").split()
            selected=tag in ("li","p") or tag=="div" and bool(set(classes)&{"command-text","mask-type","footer"})
            if tag=="li":
                for row in self.stack:
                    if row["tag"]=="li":row["nested"]=True
            self.stack.append(dict(tag=tag,selected=selected,text=[],nested=False,line=self.getpos()[0]))
            if tag in ("img","br","meta","input","link"):self.stack.pop()
        def handle_data(self,data):
            for row in self.stack:row["text"].append(data)
        def handle_endtag(self,tag):
            indices=[n for n,row in enumerate(self.stack) if row["tag"]==tag]
            if not indices:return
            n=indices[-1];row=self.stack[n];self.stack=self.stack[:n]
            text=re.sub(r"\s+"," "," ".join(row["text"])).strip()
            if row["selected"] and not row["nested"] and text:self.rows.append(dict(line=row["line"],text=text))
    parser=Rows();parser.feed(Path(path).read_text());return parser.rows

def public_features(data):
    return [feature for feature in data["features"] if feature.get("audience") != "developer" and feature.get("category") != "developer"]

def relative_logo_src(output):
    output=Path(output).resolve()
    return os.path.relpath(ROOT/"images/logo.svg",output.parent).replace(os.sep,"/")

def render(data,manual_prefix="manual/",logo_src="images/logo.svg"):
    pieces=[]
    for feature in public_features(data):
        fid=feature["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",fid):raise ValueError("Invalid feature ID: "+fid)
        title=escape(feature["title"]);summary=escape(feature.get("summary",""))
        rows=[]
        for control in feature.get("controls",[]):
            rows.append("<tr><td>"+escape(control["gesture"])+"</td><td>"+escape(control.get("result",""))+"</td></tr>")
        table=('<table><thead><tr><th scope="col">Gesture</th><th scope="col">What happens</th></tr></thead><tbody>'+"".join(rows)+"</tbody></table>") if rows else ""
        pieces.append('<article id="'+fid+'"><h2><a href="'+escape(manual_prefix,quote=True)+'#'+fid+'">'+title+"</a></h2><p>"+summary+"</p>"+table+"</article>")
    template="""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mosaic · quick reference</title><style>@@STYLE@@</style></head><body>
<a class="skip" href="#reference">Skip to controls</a><header>
<div class="mast"><img class="brand-logo" src="@@LOGO@@" alt="" width="68" height="55"><h1>MOSAIC</h1></div>
<p class="eyebrow">@@EDITION@@ / quick reference</p>
<nav aria-label="Reference links"><a href="@@MANUAL@@">Interactive manual</a><button id="theme" type="button">Switch light / dark</button></nav>
<p>Find a control here, then follow its heading for setup and full steps.</p></header>
<main id="reference" tabindex="-1"><div class="search"><label for="find">Find a control</label><input id="find" type="search" placeholder="Try masks, hold or velocity" autocomplete="off"><button id="clear" type="button">Clear</button><span id="count" role="status" aria-live="polite"></span></div><div class="catalogue">@@CARDS@@</div><footer>Keyboard: / focuses search. Escape clears search. Tab follows links and buttons.</footer></main><script>@@SCRIPT@@</script></body></html>
"""
    substitutions={"@@STYLE@@":STYLE,"@@EDITION@@":escape(data.get("edition","")),
        "@@MANUAL@@":escape(manual_prefix,quote=True),"@@LOGO@@":escape(logo_src,quote=True),
        "@@CARDS@@":"".join(pieces),"@@SCRIPT@@":SCRIPT}
    for token,value in substitutions.items():template=template.replace(token,value)
    return template

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"manual/generated/quick-reference.html")
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    output=args.output.resolve()
    manual_prefix=os.path.relpath(ROOT/"manual",output.parent).replace(os.sep,"/")+"/"
    logo_src=relative_logo_src(output)
    text=render(book.load(),manual_prefix,logo_src)
    if args.check:
        if not output.is_file() or output.read_text()!=text:raise SystemExit("Quick reference stale; regenerate")
        print("quick reference current");return
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(text)
    print("Generated "+str(output))
if __name__=="__main__":main()
