import json, os, glob
D=os.path.expanduser("~/Desktop/spytok-export/no-demo")
desc={}
vf=f"{D}/outlier_vision.json"
if os.path.exists(vf):
    byid=json.load(open(vf))
    for vid,o in byid.items(): desc[vid]=o
SB={}
sbf=os.path.expanduser("~/Desktop/spytok-export/storyboard_desc.json")
if os.path.exists(sbf):
    for k,o in json.load(open(sbf)).items():
        if k.startswith("nd_"): SB[k[3:]]=o
SBKEYS=["content_type","visual_summary","main_character","action","elements","setting","development","hook_0_3s","post_hook","retention_drivers","titles_on_screen","pacing","whats_important"]
profs=[]
for f in sorted(glob.glob(f"{D}/outliers_data/*.json")):
    d=json.load(open(f)); h=d["handle"]; outs=[]
    for o in d.get("outliers",[]):
        fr=f"outliers_frames/{h}__{o['id']}.jpg"
        de=desc.get(o["id"],{})
        tr=None
        sub=glob.glob(f"{D}/outliers_subs/{o['id']}*.vtt")
        if sub:
            import re as _re
            raw=open(sub[0]).read()
            lines=[l.strip() for l in raw.splitlines() if l.strip() and "-->" not in l and not l.startswith(("WEBVTT","Kind","Language")) and not l.isdigit()]
            seen=[]; 
            for l in lines:
                l=_re.sub(r"<[^>]+>","",l)
                if l and (not seen or seen[-1]!=l): seen.append(l)
            tr=" ".join(seen)[:1500] or None
        outs.append({"id":o["id"],"views":o["views"],"date":o["date"],"mult":o.get("mult"),
            "desc":o.get("desc"),"url":o["url"],
            "type":o.get("type","video"),"n_images":o.get("n_images"),
            "frame":fr if os.path.exists(f"{D}/{fr}") else None,
            "opening_type":de.get("opening_type"),"scene":de.get("scene"),
            "on_screen_text":de.get("on_screen_text"),"hook":de.get("hook"),"format_signature":de.get("format_signature"),
            "talking_head":de.get("talking_head"),"topic":de.get("topic"),"transcript":tr,
            "sb":{k:SB[o["id"]].get(k) for k in SBKEYS} if o["id"] in SB else None})
    if not outs: continue
    profs.append({"handle":h,"layer":d["layer"],"verdict":d["verdict"],"similarity":d.get("similarity"),
        "median":d["median"],"n_videos":d["n_videos"],"n_outliers":len(outs),
        "n_carousels":sum(1 for o in outs if o.get("type")=="carousel"),
        "top_views":max((o["views"] for o in outs),default=0),
        "max_mult":max((o["mult"] or 0 for o in outs),default=0),
        "profile_url":f"https://www.tiktok.com/@{h}","outliers":outs})
profs.sort(key=lambda p:-p["top_views"])
tot={"profiles":len(profs),"outliers":sum(p["n_outliers"] for p in profs)}
open(f"{D}/data_outliers.js","w").write("window.OUT="+json.dumps({"profiles":profs,"totals":tot},ensure_ascii=False,separators=(",",":"))+";")
fr=len(glob.glob(f"{D}/outliers_frames/*.jpg"))
print("data_outliers.js:",round(os.path.getsize(f'{D}/data_outliers.js')/1e6,1),"MB | perfiles",len(profs),"| outliers",tot["outliers"],"| frames",fr)
