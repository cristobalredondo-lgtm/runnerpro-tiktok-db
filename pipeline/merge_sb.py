import json,os,re,sys
D=os.path.expanduser("~/Desktop/spytok-export")
out=f"{D}/storyboard_desc.json"
sb=json.load(open(out)) if os.path.exists(out) else {}
raw=json.load(open(sys.argv[1]))['result']['raw']
added=0
for s in raw:
    if not isinstance(s,str) or s.startswith("API Error"): continue
    m=re.search(r'\[.*\]',s,re.S)
    if not m: continue
    try: arr=json.loads(m.group(0))
    except: continue
    for o in arr:
        if isinstance(o,dict) and o.get('key') and o['key'] not in sb:
            sb[o['key']]=o; added+=1
json.dump(sb,open(out,'w'),ensure_ascii=False)
print(f"sb +{added} | total {len(sb)} / 5056")
