"""Speed-test nodes for the watanare H3 runner (ComfyUI custom node, single file).

WNSaveFast: saves the PNG frames listed in `keep` (fast compression) before returning, then in a background thread pipes
            the full clip into ffmpeg (`mp4_path`, libx264 crf 14 BT.709) and, with save_rest, writes the remaining PNGs.
            The prompt returns without waiting for the encode; the mp4 appears atomically (written as .part, then renamed).
WNProfile:  wraps the model and runs torch.profiler on one sampling step; writes a kernel table + GPU busy time to `path`.
"""
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import torch
from PIL import Image

import folder_paths


class WNSaveFast:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"images": ("IMAGE",), "filename_prefix": ("STRING", {"default": "wn/frame"}),
                             "keep": ("STRING", {"default": "-1"}), "mp4_path": ("STRING", {"default": ""}),
                             "compress_level": ("INT", {"default": 1, "min": 0, "max": 9}),
                             "save_rest": ("BOOLEAN", {"default": True})}}

    RETURN_TYPES = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "wn"

    def save(self, images, filename_prefix, keep, mp4_path, compress_level, save_rest=True):
        arr = (images.clamp(0, 1) * 255).round().to(torch.uint8).cpu().numpy()
        n, h, w = arr.shape[:3]
        d = os.path.join(folder_paths.get_output_directory(), os.path.dirname(filename_prefix))
        os.makedirs(d, exist_ok=True)
        base = os.path.basename(filename_prefix)
        idx = sorted({(int(k) % n) for k in keep.split(",") if k.strip()}) if keep.strip() != "all" else list(range(n))

        def png(i):
            Image.fromarray(arr[i]).save(os.path.join(d, f"{base}_{i + 1:05d}_.png"), compress_level=compress_level)

        with ThreadPoolExecutor(8) as ex:
            list(ex.map(png, idx))
        rest = [i for i in range(n) if i not in idx] if save_rest else []

        def enc():
            if mp4_path:
                tmp = mp4_path + ".part.mp4"
                p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-framerate", "24", "-i", "-",
                                      "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                                      "-color_trc", "bt709", tmp], stdin=subprocess.PIPE)
                p.stdin.write(arr.tobytes())
                p.stdin.close()
                if p.wait() == 0:
                    os.replace(tmp, mp4_path)
            if rest:
                with ThreadPoolExecutor(4) as ex2:
                    list(ex2.map(png, rest))

        if mp4_path or rest:
            threading.Thread(target=enc, daemon=True).start()
        return {"ui": {}}


class WNProfile:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"model": ("MODEL",), "step": ("INT", {"default": 3, "min": 0, "max": 100}), "path": ("STRING", {"default": "/tmp/wn_prof.txt"})}}

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "apply"
    CATEGORY = "wn"

    def apply(self, model, step, path):
        st = {"i": 0, "t": None}
        log = []

        def wrapper(apply_model, args):
            i = st["i"]
            st["i"] += 1
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            if i != step:
                out = apply_model(args["input"], args["timestep"], **args["c"])
                torch.cuda.synchronize()
                log.append((i, time.perf_counter() - t0, None))
                return out
            acts = [torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA]
            with torch.profiler.profile(activities=acts) as p:
                out = apply_model(args["input"], args["timestep"], **args["c"])
                torch.cuda.synchronize()
            wall = time.perf_counter() - t0
            ka = p.key_averages()
            key = "self_device_time_total" if hasattr(ka[0], "self_device_time_total") else "self_cuda_time_total"
            busy = sum(getattr(e, key) for e in ka) / 1e6
            groups = {}
            for e in ka:
                nm = e.key.lower()
                g = ("memcpy HtoD" if "htod" in nm or "h2d" in nm else "memcpy DtoH" if "dtoh" in nm or "d2h" in nm else "memcpy/memset other" if "memcpy" in nm or "memset" in nm
                     else "attention" if any(s in nm for s in ("attn", "attention", "flash", "sdpa", "sol_", "fmha")) else
                     "gemm/linear" if any(s in nm for s in ("gemm", "mm", "linear", "cutlass", "nvfp4", "fp4", "matmul")) else "other")
                groups[g] = groups.get(g, 0) + getattr(e, key) / 1e6
            with open(path, "w") as f:
                f.write(f"profiled step {i}: wall {wall:.3f}s, summed self device time {busy:.3f}s\n")
                f.write("groups (s): " + ", ".join(f"{k} {v:.3f}" for k, v in sorted(groups.items(), key=lambda x: -x[1])) + "\n")
                f.write("unprofiled steps (s): " + ", ".join(f"{a}:{b:.2f}" for a, b, _ in log) + "\n\n")
                f.write(ka.table(sort_by=key, row_limit=45, max_name_column_width=90))
            return out

        m = model.clone()
        m.set_model_unet_function_wrapper(wrapper)
        return (m,)


NODE_CLASS_MAPPINGS = {"WNSaveFast": WNSaveFast, "WNProfile": WNProfile}
