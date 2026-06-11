import json, os, re, glob, math, time, subprocess, datetime
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from PIL import Image

D = os.path.expanduser("~/Desktop/spytok-export")
ND = f"{D}/no-demo"; SB = f"{D}/storyboards"; FR = f"{ND}/outliers_frames"
YTDLP = [f"{D}/venv313/bin/python", "-m", "yt_dlp"]
PROG = f"{D}/carousel_sweep_progress.txt"
OUTMETA = f"{D}/carousel_sweep.json"

WINDOW_DAYS = 547          # 18 meses
OUTLIER_MULT = 3.0
OUTLIER_FLOOR = 30000
CAND_CAP = 20              # candidatos por perfil
ENUM_CAP = 400

cutoff = time.time() - WINDOW_DAYS * 86400
UNIV = re.compile(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>', re.S)

# known ids per handle (skip existing outliers)
known = {}
handles = []
for f in sorted(glob.glob(f"{ND}/outliers_data/*.json")):
    d = json.load(open(f))
    h = d["handle"]; handles.append(h)
    known[h] = {str(o["id"]) for o in d.get("outliers", [])}

meta = json.load(open(OUTMETA)) if os.path.exists(OUTMETA) else {}
done_profiles = set(meta.get("_done_profiles", []))
results = meta.get("items", {})

def enum_profile(h):
    try:
        r = subprocess.run(YTDLP + ["--flat-playlist", "--playlist-end", str(ENUM_CAP),
                                    "--impersonate", "chrome",
                                    "--print", "%(view_count)s|%(id)s|%(timestamp)s",
                                    f"https://www.tiktok.com/@{h}"],
                           capture_output=True, text=True, timeout=420)
        posts = []
        for line in r.stdout.splitlines():
            p = line.strip().split("|")
            if len(p) != 3: continue
            try: views = int(p[0])
            except: continue
            try: ts = int(p[2])
            except: ts = None
            posts.append({"views": views, "id": p[1], "ts": ts})
        return posts
    except Exception:
        return []

def fetch_item(h, vid):
    url = f"https://www.tiktok.com/@{h}/video/{vid}"
    try:
        r = requests.get(url, impersonate="chrome", timeout=30)
        if r.status_code != 200: return None
        m = UNIV.search(r.text)
        if not m: return None
        d = json.loads(m.group(1))
        return d.get("__DEFAULT_SCOPE__", {}).get("webapp.video-detail", {}).get("itemInfo", {}).get("itemStruct", {})
    except Exception:
        return None

def build_grid(imgs, key):
    sb = f"{SB}/{key}.jpg"
    W = 360; rs = []
    for im in imgs:
        h2 = int(im.height * W / im.width); rs.append(im.resize((W, h2), Image.LANCZOS))
    n = len(rs); cols = min(n, 5); rows = math.ceil(n / cols)
    cellh = max(im.height for im in rs); pad = 4
    canvas = Image.new("RGB", (cols * W + (cols + 1) * pad, rows * cellh + (rows + 1) * pad), (0, 0, 0))
    for idx, im in enumerate(rs):
        canvas.paste(im, (pad + (idx % cols) * (W + pad), pad + (idx // cols) * (cellh + pad)))
    canvas.save(sb, "JPEG", quality=70, optimize=True)
    return os.path.exists(sb)

def work(h):
    found = 0
    posts = enum_profile(h)
    inwin = [p for p in posts if p["ts"] and p["ts"] >= cutoff]
    if len(inwin) < 5: inwin = posts  # perfil poco activo: usar todo
    vs = sorted(p["views"] for p in inwin if p["views"])
    if not vs: return (h, 0, 0)
    med = vs[len(vs)//2] or 1
    cands = [p for p in inwin if p["views"] and p["views"] >= OUTLIER_FLOOR
             and p["views"]/max(med,1) >= OUTLIER_MULT and p["id"] not in known.get(h, set())]
    cands.sort(key=lambda p: -p["views"])
    cands = cands[:CAND_CAP]
    for p in cands:
        vid = p["id"]; key = f"nd_{vid}"
        if key in results: continue
        item = fetch_item(h, vid)
        if not item: continue
        ip = item.get("imagePost")
        if not ip: continue  # es video, fuera
        urls = []
        for im in ip.get("images", []):
            ul = im.get("imageURL", {}).get("urlList", [])
            if ul: urls.append(ul[0])
        if not urls: continue
        imgs = []
        for iu in urls[:12]:
            try:
                ir = requests.get(iu, impersonate="chrome", timeout=30)
                if ir.status_code == 200:
                    imgs.append(Image.open(BytesIO(ir.content)).convert("RGB"))
            except Exception: pass
        if not imgs: continue
        if not build_grid(imgs, key): continue
        # frame para dashboard = primera imagen
        fr = f"{FR}/{h}__{vid}.jpg"
        if not os.path.exists(fr):
            im0 = imgs[0]; w = 360
            im0.resize((w, int(im0.height*w/im0.width)), Image.LANCZOS).save(fr, "JPEG", quality=70, optimize=True)
        st = item.get("stats", {}) or {}
        ct = item.get("createTime")
        results[key] = {
            "id": vid, "handle": h,
            "views": p["views"], "mult": round(p["views"]/max(med,1), 1),
            "median": med,
            "date": datetime.datetime.utcfromtimestamp(int(ct)).strftime("%Y-%m-%d") if ct else None,
            "desc": (item.get("desc") or "")[:300],
            "likes": st.get("diggCount"), "comments": st.get("commentCount"),
            "saves": st.get("collectCount"), "shares": st.get("shareCount"),
            "n_images": len(urls),
            "url": f"https://www.tiktok.com/@{h}/photo/{vid}",
            "type": "carousel",
        }
        found += 1
    return (h, len(cands), found)

todo = [h for h in handles if h not in done_profiles]
total = len(todo); done_n = [0]; tot_found = [sum(1 for k in results if not k.startswith('_'))]
open(PROG, "w").write(f"0/{total} carousels={tot_found[0]}\n")

with ThreadPoolExecutor(max_workers=4) as ex:
    futs = {ex.submit(work, h): h for h in todo}
    for fu in as_completed(futs):
        h = futs[fu]
        try:
            _, nc, nf = fu.result()
            tot_found[0] += nf
        except Exception:
            pass
        done_profiles.add(h)
        done_n[0] += 1
        meta = {"_done_profiles": sorted(done_profiles), "items": results}
        json.dump(meta, open(OUTMETA, "w"), ensure_ascii=False)
        open(PROG, "w").write(f"{done_n[0]}/{total} carousels={tot_found[0]} last={h}\n")

json.dump({"_done_profiles": sorted(done_profiles), "items": results}, open(OUTMETA, "w"), ensure_ascii=False)
open(PROG, "w").write(f"DONE {done_n[0]}/{total} carousels={tot_found[0]}\n")
print(f"DONE perfiles={done_n[0]} carruseles nuevos={tot_found[0]}")
