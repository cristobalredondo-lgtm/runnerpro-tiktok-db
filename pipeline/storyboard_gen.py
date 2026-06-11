import json, os, subprocess, glob, math
from concurrent.futures import ThreadPoolExecutor, as_completed
D = os.path.expanduser("~/Desktop/spytok-export")
ND = f"{D}/no-demo"
SB = f"{D}/storyboards"; os.makedirs(SB, exist_ok=True)
PROG = f"{D}/storyboard_progress.txt"

# --- build targets: no-demo >=10x + all demo ---
targets = []  # (key, url)  key = 'nd_<id>' or 'dm_<id>'
seen = set()
for f in glob.glob(f"{ND}/outliers_data/*.json"):
    d = json.load(open(f)); h = d["handle"]
    for o in d.get("outliers", []):
        if (o.get("mult") or 0) >= 10:
            k = f"nd_{o['id']}"
            if k in seen: continue
            seen.add(k)
            targets.append((k, f"https://www.tiktok.com/@{h}/video/{o['id']}", o['id']))
demo = json.load(open(f"{D}/demo_videos.json"))
for vid, v in demo.items():
    k = f"dm_{vid}"
    if k in seen: continue
    seen.add(k)
    url = v.get("videoLink") or v.get("postLink")
    if url: targets.append((k, url, vid))

todo = [(k, u, vid) for (k, u, vid) in targets if not os.path.exists(f"{SB}/{k}.jpg")]
total = len(todo); done = [0]; ok = [0]
open(PROG, "w").write(f"0/{total} (targets {len(targets)})\n")

def make(k, url, vid):
    sb = f"{SB}/{k}.jpg"
    if os.path.exists(sb): return True
    mp4 = f"{D}/_sb_{k}.mp4"
    try:
        if url.endswith(".mp4"):
            subprocess.run(["curl","-s","-L","-o",mp4,"--max-time","90",url], timeout=100, check=False)
        else:
            subprocess.run(["yt-dlp","-q","--no-warnings","-o",mp4,url], timeout=120, check=False)
        real = mp4 if os.path.exists(mp4) else (glob.glob(f"{D}/_sb_{k}.*") or [None])[0]
        if not (real and os.path.exists(real) and os.path.getsize(real) > 1000):
            raise Exception("no dl")
        # duration
        dur = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",real],
                             capture_output=True, text=True).stdout.strip()
        try: n = max(1, min(36, math.ceil(float(dur))))
        except: n = 9
        cols = min(n, 6); rows = math.ceil(n / cols)
        # fps=1 grabs ~1 frame/sec; tile into grid; scale each to 240w
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",real,
                        "-frames:v","1","-vf",f"fps=1,scale=240:-1,tile={cols}x{rows}:padding=2:color=black",
                        sb], timeout=90, check=False)
        for x in glob.glob(f"{D}/_sb_{k}.*"):
            try: os.remove(x)
            except: pass
        return os.path.exists(sb)
    except Exception:
        for x in glob.glob(f"{D}/_sb_{k}.*"):
            try: os.remove(x)
            except: pass
        return False

with ThreadPoolExecutor(max_workers=6) as ex:
    futs = {ex.submit(make, k, u, vid): k for (k, u, vid) in todo}
    for fu in as_completed(futs):
        done[0] += 1
        if fu.result(): ok[0] += 1
        if done[0] % 25 == 0: open(PROG, "w").write(f"{done[0]}/{total} ok={ok[0]}\n")
open(PROG, "w").write(f"DONE {done[0]}/{total} ok={ok[0]}\n")
