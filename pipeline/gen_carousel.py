import json, os, re, glob, math
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from PIL import Image

D = os.path.expanduser("~/Desktop/spytok-export"); ND = f"{D}/no-demo"; SB = f"{D}/storyboards"
META = f"{D}/carousel_meta.json"; PROG = f"{D}/gen_carousel_progress.txt"

desc = json.load(open(f"{D}/storyboard_desc.json"))
have_desc = set(desc.keys())

# build targets: missing dm (86) + missing nd >=10x photo-posts
targets = {}  # key -> url
demo = json.load(open(f"{D}/demo_videos.json"))
for vid, v in demo.items():
    k = f"dm_{vid}"
    if k in have_desc or os.path.exists(f"{SB}/{k}.jpg"): continue
    u = v.get("postLink") or v.get("videoLink")
    if u: targets[k] = u
seen = set()
for f in glob.glob(f"{ND}/outliers_data/*.json"):
    d = json.load(open(f)); h = d["handle"]
    for o in d.get("outliers", []):
        if (o.get("mult") or 0) >= 10:
            i = str(o["id"]); k = f"nd_{i}"
            if k in have_desc or k in seen or os.path.exists(f"{SB}/{k}.jpg"): continue
            seen.add(k); targets[k] = f"https://www.tiktok.com/@{h}/video/{i}"

items = list(targets.items())
total = len(items); done = [0]; ok = [0]
meta = json.load(open(META)) if os.path.exists(META) else {}
open(PROG, "w").write(f"0/{total}\n")

UNIV = re.compile(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>', re.S)

def build(k, url):
    sb = f"{SB}/{k}.jpg"
    if os.path.exists(sb): return ("skip", k)
    try:
        r = requests.get(url, impersonate="chrome", timeout=30)
        if r.status_code != 200: return ("err", k)
        m = UNIV.search(r.text)
        if not m: return ("err", k)
        d = json.loads(m.group(1))
        item = d.get("__DEFAULT_SCOPE__", {}).get("webapp.video-detail", {}).get("itemInfo", {}).get("itemStruct", {})
        ip = item.get("imagePost")
        if not ip: return ("novel", k)   # not a carousel (and no video earlier) -> skip
        urls = []
        for im in ip.get("images", []):
            ul = im.get("imageURL", {}).get("urlList", [])
            if ul: urls.append(ul[0])
        if not urls: return ("err", k)
        imgs = []
        for iu in urls:
            try:
                ir = requests.get(iu, impersonate="chrome", timeout=30)
                if ir.status_code == 200:
                    imgs.append(Image.open(BytesIO(ir.content)).convert("RGB"))
            except Exception: pass
        if not imgs: return ("err", k)
        # build grid: width 360 each, cols up to 5
        W = 360
        rs = []
        for im in imgs:
            h2 = int(im.height * W / im.width); rs.append(im.resize((W, h2), Image.LANCZOS))
        n = len(rs); cols = min(n, 5); rows = math.ceil(n / cols)
        cellh = max(im.height for im in rs); pad = 4
        canvas = Image.new("RGB", (cols * W + (cols + 1) * pad, rows * cellh + (rows + 1) * pad), (0, 0, 0))
        for idx, im in enumerate(rs):
            cx = idx % cols; cy = idx // cols
            canvas.paste(im, (pad + cx * (W + pad), pad + cy * (cellh + pad)))
        canvas.save(sb, "JPEG", quality=70, optimize=True)
        return ("ok", k, n, (item.get("desc") or "")[:300])
    except Exception:
        return ("err", k)

with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(build, k, u) for (k, u) in items]
    for fu in as_completed(futs):
        res = fu.result(); done[0] += 1
        if res[0] == "ok":
            ok[0] += 1; _, k, n, dsc = res
            meta[k] = {"type": "carousel", "n_images": n, "desc": dsc}
        if done[0] % 10 == 0:
            json.dump(meta, open(META, "w"), ensure_ascii=False)
            open(PROG, "w").write(f"{done[0]}/{total} ok={ok[0]}\n")
json.dump(meta, open(META, "w"), ensure_ascii=False)
open(PROG, "w").write(f"DONE {done[0]}/{total} ok={ok[0]}\n")
print(f"DONE {done[0]}/{total} ok={ok[0]} carruseles")
