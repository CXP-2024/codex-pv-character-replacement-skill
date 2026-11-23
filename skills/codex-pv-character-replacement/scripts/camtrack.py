"""Per-frame camera motion of the source and of our cut over a frame range (from the 2026-11-22 retrospective of a 69-second ten-character replacement MAD).

ORB + RANSAC similarity between consecutive frames at 960x480: scale (<1 = pulling back / zooming out), dx, dy (pixels at 960 wide),
inlier count. Use it (a) before H3 to mark one-way zooms and pans (start keyframe at the close end, one forward chain) and (b) after
assembly to catch back-and-forth or reversed camera moves. Rows with very few inliers are cuts, flashes or heavy blur: ignore them.

python -I camtrack.py --src source.mp4 [--cut ours.mp4] --range 232 267 [--ffmpeg path]
"""
import argparse, os, shutil, subprocess
import numpy as np, cv2


def ffmpeg_path(arg):
    for p in (arg, os.environ.get("FFMPEG"), shutil.which("ffmpeg")):
        if p and os.path.exists(p):
            return p
    raise SystemExit("ffmpeg not found: pass --ffmpeg or set FFMPEG")


def load(ff, path, s, e, W=960, H=480):
    raw = subprocess.run([ff, "-v", "error", "-i", path, "-vf", f"trim=start_frame={s}:end_frame={e},setpts=PTS-STARTPTS,scale={W}:{H}",
                          "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W)


def track(fr):
    orb = cv2.ORB_create(2000); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    out = [(1.0, 0.0, 0.0, 0)]
    for a, b in zip(fr[:-1], fr[1:]):
        ka, da = orb.detectAndCompute(a, None); kb, db = orb.detectAndCompute(b, None)
        if da is None or db is None:
            out.append((np.nan, np.nan, np.nan, 0)); continue
        m = bf.match(da, db)
        if len(m) < 12:
            out.append((np.nan, np.nan, np.nan, len(m))); continue
        pa = np.float32([ka[x.queryIdx].pt for x in m]); pb = np.float32([kb[x.trainIdx].pt for x in m])
        M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=2.0, maxIters=3000)
        if M is None:
            out.append((np.nan, np.nan, np.nan, 0)); continue
        out.append((float(np.hypot(M[0, 0], M[1, 0])), float(M[0, 2]), float(M[1, 2]), int(inl.sum())))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True); ap.add_argument("--cut"); ap.add_argument("--range", nargs=2, type=int, required=True)
    ap.add_argument("--ffmpeg")
    a = ap.parse_args()
    ff = ffmpeg_path(a.ffmpeg); s, e = a.range
    A = track(load(ff, a.src, s, e)); B = track(load(ff, a.cut, s, e)) if a.cut else None
    print("frame | source: scale dx dy inliers" + (" | ours: scale dx dy inliers" if B else ""))
    for i in range(e - s):
        line = "%d | %.3f %6.1f %6.1f %4d" % ((s + i,) + tuple(A[i]))
        if B:
            line += " | %.3f %6.1f %6.1f %4d" % tuple(B[i])
        print(line)
    def total(T):
        sc = [t[0] for t in T[1:] if t[3] >= 100 and np.isfinite(t[0])]
        return float(np.prod(sc)) if sc else float("nan")
    print("product of reliable per-frame scales: source %.3f" % total(A) + (" | ours %.3f" % total(B) if B else ""))


if __name__ == "__main__":
    main()
