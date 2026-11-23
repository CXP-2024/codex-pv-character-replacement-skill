"""Cut audit for a character-replacement edit against its source (from the 2026-11-22 retrospective of a 69-second ten-character replacement MAD).

Three checks, all against the source at the same frame:
  1. Same-drawing test at every shot boundary (--bounds) and every source jump: ORB + RANSAC similarity between the frames on both sides.
     Many inliers = the SAME drawing (zoom / stretch / shift), not a cut. Also flags boundaries that are not on the biggest source jump
     within +-4 frames.
  2. Frames where OUR cut jumps but the source does not (our neighbour difference exceeds the source's by --jump, default 40).
  3. Optional contact sheets: every --step-th frame source above ours (--scan-dir), and every kept-source frame (--keep-sheet, needs
     --ledger: a JSON list of [frame, kind, index] where kind "src" means the source frame was kept).

python -I cut_audit.py --src source.mp4 --cut ours.mp4 [--bounds 61,113,160 | --bounds bounds.json] [--ledger ledger.json]
                       [--scan-dir sheets/] [--keep-sheet keep.jpg] [--out audit.json] [--ffmpeg path]
"""
import argparse, json, os, shutil, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont


def ffmpeg_path(arg):
    for p in (arg, os.environ.get("FFMPEG"), shutil.which("ffmpeg")):
        if p and os.path.exists(p):
            return p
    raise SystemExit("ffmpeg not found: pass --ffmpeg or set FFMPEG")


def load(ff, path, W, H, fmt="rgb24"):
    ch = 3 if fmt == "rgb24" else 1
    raw = subprocess.run([ff, "-v", "error", "-i", path, "-vf", f"scale={W}:{H}", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", fmt, "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8)
    return a.reshape(-1, H, W, ch) if ch == 3 else a.reshape(-1, H, W)


def sim_fit(a, b, orb, bf):
    ka, da = orb.detectAndCompute(a, None); kb, db = orb.detectAndCompute(b, None)
    if da is None or db is None or len(ka) < 20 or len(kb) < 20:
        return None
    m = bf.match(da, db)
    if len(m) < 20:
        return None
    pa = np.float32([ka[x.queryIdx].pt for x in m]); pb = np.float32([kb[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=4000)
    if M is None:
        return None
    n = int(inl.sum())
    return dict(scale=round(float(np.hypot(M[0, 0], M[1, 0])), 3), tx=round(float(M[0, 2]), 1), ty=round(float(M[1, 2]), 1), inliers=n,
                ratio=round(n / len(m), 2), same=n >= 25 and n / len(m) >= 0.25)


def sheet(frames_a, frames_b, labels, path, cols=9):
    H, W = frames_a[0].shape[:2]
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13) if os.path.exists("C:/Windows/Fonts/msyh.ttc") else ImageFont.load_default()
    rows = (len(labels) + cols - 1) // cols
    two = frames_b is not None
    s = Image.new("RGB", (cols * (W + 2), rows * ((2 if two else 1) * H + 18)), "white"); d = ImageDraw.Draw(s)
    for i, lab in enumerate(labels):
        x = (i % cols) * (W + 2); y = (i // cols) * ((2 if two else 1) * H + 18)
        s.paste(Image.fromarray(frames_a[i]), (x, y))
        if two:
            s.paste(Image.fromarray(frames_b[i]), (x, y + H + 1))
        d.text((x + 3, y + (2 if two else 1) * H + 2), lab, fill="black", font=font)
    s.save(path, quality=82)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True); ap.add_argument("--cut", required=True)
    ap.add_argument("--bounds", default=""); ap.add_argument("--ledger"); ap.add_argument("--jump", type=float, default=40)
    ap.add_argument("--scan-dir"); ap.add_argument("--step", type=int, default=4); ap.add_argument("--keep-sheet")
    ap.add_argument("--out"); ap.add_argument("--ffmpeg")
    a = ap.parse_args()
    ff = ffmpeg_path(a.ffmpeg)
    bounds = []
    if a.bounds:
        bounds = json.load(open(a.bounds)) if a.bounds.endswith(".json") else [int(x) for x in a.bounds.split(",") if x.strip()]
    led = json.load(open(a.ledger, encoding="utf8")) if a.ledger else None

    src = load(ff, a.src, 320, 160).astype(np.int16); ours = load(ff, a.cut, 320, 160).astype(np.int16)
    n = min(len(src), len(ours))
    d_src = np.r_[0, np.abs(np.diff(src[:n], axis=0)).mean(axis=(1, 2, 3))]
    d_ours = np.r_[0, np.abs(np.diff(ours[:n], axis=0)).mean(axis=(1, 2, 3))]

    g = load(ff, a.src, 640, 320, "gray")
    orb = cv2.ORB_create(1500); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    spikes = [k for k in range(1, n) if d_src[k] > 18 and d_src[k] > 2.5 * np.median(d_src[max(1, k - 6):k + 7])]
    rows = []
    print("== 1. boundaries (B) and source jumps: same drawing? on the biggest jump within +-4? ==")
    for k in sorted(set(bounds) | set(spikes)):
        if not 1 <= k < n:
            continue
        f1 = sim_fit(g[k - 1], g[k], orb, bf); f2 = sim_fit(g[max(0, k - 2)], g[min(n - 1, k + 1)], orb, bf)
        w = range(max(1, k - 4), min(n, k + 5)); mx = max(w, key=lambda i: d_src[i])
        off = mx if (k in bounds and mx != k and d_src[mx] > d_src[k] + 15) else None
        same = bool((f1 and f1["same"]) or (f2 and f2["same"]))
        rows.append(dict(k=k, boundary=k in bounds, d_src=round(float(d_src[k]), 1), d_ours=round(float(d_ours[k]), 1), fit=f1, fit2=f2,
                         same_drawing=same, biggest_jump_at=off))
        if k in bounds or same:
            f = f1 if f1 and f1["same"] else f2
            print(k, "B" if k in bounds else " ", "SAME drawing scale %.3f" % f["scale"] if same else "cut", "| src %.0f ours %.0f" % (d_src[k], d_ours[k]),
                  "| BOUNDARY OFF: biggest jump at %d" % off if off else "")
    jumps = [(k, round(float(d_src[k])), round(float(d_ours[k]))) for k in range(1, n) if d_ours[k] - d_src[k] > a.jump]
    print("== 2. our jumps that the source does not have (ours - source > %g): check each by eye ==" % a.jump)
    print(jumps)
    if led:
        runs = []
        for k, kind, m in led[:n]:
            if kind == "src":
                if runs and runs[-1][1] == k - 1:
                    runs[-1][1] = k
                else:
                    runs.append([k, k])
        print("== kept source runs (look at every frame for people) ==", [tuple(r) for r in runs])
    if a.out:
        json.dump(dict(d_src=[round(float(x), 2) for x in d_src], d_ours=[round(float(x), 2) for x in d_ours], rows=rows, jumps=jumps), open(a.out, "w"))
    del src, ours, g
    if a.scan_dir or a.keep_sheet:
        S = load(ff, a.src, 240, 120); O = load(ff, a.cut, 240, 120)
        if a.scan_dir:
            os.makedirs(a.scan_dir, exist_ok=True)
            ks = [k for k in range(0, n, a.step) if not led or led[k][1] != "src"]
            per = 54
            for p in range(0, len(ks), per):
                part = ks[p:p + per]
                labs = [f"{k} {led[k][1][-14:]}:{led[k][2]}" if led else str(k) for k in part]
                sheet([S[k] for k in part], [O[k] for k in part], labs, os.path.join(a.scan_dir, f"scan_{p // per:02d}.jpg"))
            print("scan sheets ->", a.scan_dir)
        if a.keep_sheet and led:
            ks = [k for k, kind, m in led[:n] if kind == "src"]
            sheet([S[k] for k in ks], None, [str(k) for k in ks], a.keep_sheet, cols=14)
            print("kept-source sheet ->", a.keep_sheet)


if __name__ == "__main__":
    main()
