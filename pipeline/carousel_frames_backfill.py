import json, os, re, glob
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from curl_cffi import requests
from PIL import Image

D = os.path.expanduser("~/Desktop/spytok-export")
FR = f"{D}/no-demo/outliers_frames"
UNIV = re.compile(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>', re.S)

cmeta = json.load(open(f"{D}/carousel_meta.json"))
known = [k[3:] for k in cmeta if k.startswith("nd_")]
id2h = {}
for f in glob.glob(f"{D}/no-demo/outliers_data/*.json"):
    d = json.load(open(f))
    for o in d["outliers"]:
        id2h[str(o["id"])] = d["handle"]

todo = [(i, id2h[i]) for i in known if i in id2h
        and not os.path.exists(f"{FR}/{id2h[i]}__{i}.jpg")]
print("backfill frames:", len(todo))

def work(t):
    vid, h = t
    try:
        r = requests.get(f"https://www.tiktok.com/@{h}/video/{vid}", impersonate="chrome", timeout=30)
        if r.status_code != 200: return 0
        m = UNIV.search(r.text)
        if not m: return 0
        item = json.loads(m.group(1)).get("__DEFAULT_SCOPE__", {}).get("webapp.video-detail", {}).get("itemInfo", {}).get("itemStruct", {})
        ip = item.get("imagePost")
        if not ip: return 0
        ims = ip.get("images", [])
        if not ims: return 0
        ul = ims[0].get("imageURL", {}).get("urlList", [])
        if not ul: return 0
        ir = requests.get(ul[0], impersonate="chrome", timeout=30)
        if ir.status_code != 200: return 0
        im = Image.open(BytesIO(ir.content)).convert("RGB")
        w = 360
        im.resize((w, int(im.height * w / im.width)), Image.LANCZOS).save(
            f"{FR}/{h}__{vid}.jpg", "JPEG", quality=70, optimize=True)
        return 1
    except Exception:
        return 0

done = 0
with ThreadPoolExecutor(max_workers=4) as ex:
    for n, r in enumerate(ex.map(work, todo), 1):
        done += r
        if n % 50 == 0: print(f"{n}/{len(todo)} ok={done}", flush=True)
print(f"DONE {done}/{len(todo)}")
