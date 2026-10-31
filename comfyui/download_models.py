"""Download the H3 Ref2VA models listed in models.json into ComfyUI/models and verify their SHA-256.

usage: python download_models.py /path/to/ComfyUI     (needs: pip install huggingface_hub)
About 34 GB in total. Files that already exist are only verified.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

comfy = Path(sys.argv[1])
here = Path(__file__).resolve().parent
for m in json.loads((here / "models.json").read_text(encoding="utf-8")):
    dest = comfy / "models" / m["destination"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        got = hf_hub_download(m["repo"], m["file"], revision=m["revision"], local_dir=comfy / "models" / "_downloads")
        shutil.move(got, dest)
    h = hashlib.sha256()
    with dest.open("rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    assert h.hexdigest() == m["sha256"], f"hash mismatch: {dest}"
    print("verified", dest.name, flush=True)
