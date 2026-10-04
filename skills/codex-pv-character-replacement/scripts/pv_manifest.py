"""CPU-only PV frame mapping, frozen input checks and delivery ledger validation."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def emit(value, path=None):
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        with Path(path).open("x", encoding="utf-8") as stream:
            stream.write(text)
    else:
        print(text, end="")


def positive_int(value, label):
    if type(value) is not int or value < 1:
        raise ValueError(f"{label} must be a positive integer")


def frame_map(source_count, target_count):
    """Uniform nearest-frame sampling, exact integer half-up; not interpolation."""
    positive_int(source_count, "source_count")
    positive_int(target_count, "target_count")
    if target_count == 1:
        return [0]
    d = target_count - 1
    return [(2 * i * (source_count - 1) + d) // (2 * d)
            for i in range(target_count)]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def local_file(root, relative):
    """Keep portable manifests inside their project; do not follow escaping symlinks."""
    path = Path(relative)
    if path.is_absolute():
        raise ValueError("Manifest asset paths must be project-relative")
    root = Path(root).resolve()
    result = (root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError(f"Asset escapes project root: {relative}")
    if not result.is_file():
        raise ValueError(f"Missing asset: {relative}")
    return result


def validate_job(job, profile):
    start, end = job["start"], job["end"]
    if type(start) is not int or type(end) is not int or start < 0 or end <= start:
        raise ValueError("Expected nonempty zero-based half-open source range")
    for key in ("width", "height", "model_frames", "steps"):
        positive_int(job[key], key)
    if type(job["seed"]) is not int or job["seed"] < 0:
        raise ValueError("Seed must be a frozen nonnegative integer")
    refs = job["references"]
    if not isinstance(refs, list) or not all(
            isinstance(x, dict) and x.get("path") and x.get("role") for x in refs):
        raise ValueError("References require ordered path and role records")
    if len(refs) > profile["max_references"]:
        raise ValueError("Reference cap exceeded")
    if job["model_frames"] > profile["max_model_frames"]:
        raise ValueError("Model frame cap exceeded")
    if end - start > profile["max_source_frames"]:
        raise ValueError("Source span exceeds this production profile")
    for key in ("width", "height"):
        if job[key] > profile["max_" + key] or job[key] % profile["dimension_step"]:
            raise ValueError(f"Invalid {key} for this profile")
    step, offset = profile["frame_step"], profile["frame_offset"]
    if job["model_frames"] < offset or (job["model_frames"] - offset) % step:
        raise ValueError("Unsupported model-frame count")
    mode = job["mode"]
    if mode not in ("Ref2VA", "FL2VA"):
        raise ValueError("This helper validates only Ref2VA and FL2VA")
    if mode == "FL2VA" and (len(refs) != 2 or [x["role"] for x in refs] != ["first", "last"]):
        raise ValueError("FL2VA requires ordered first and last frame references")
    if mode == "Ref2VA" and (not refs or not job.get("source")):
        raise ValueError("Ref2VA requires source video and references")
    if not job.get("cast") and any(x["role"] == "identity" for x in refs):
        raise ValueError("No-cast job must not import an identity portrait")
    if not job.get("id") or not job.get("prompt"):
        raise ValueError("Job requires explicit id and prompt")


def freeze(root, job_path, profile_path):
    job = read_json(local_file(root, job_path))
    profile = read_json(local_file(root, profile_path))
    validate_job(job, profile)
    items = [(job_path, "job"), (profile_path, "profile"), (job["prompt"], "prompt")]
    if job.get("source"):
        items.append((job["source"], "source"))
    items += [(x["path"], f"reference:{i}:{x['role']}")
              for i, x in enumerate(job["references"], 1)]
    assets = [{"path": p, "role": role, "sha256": digest(local_file(root, p))}
              for p, role in items]
    return {"schema": 1, "job_id": job["id"], "status": "ready_for_review",
            "assets": assets, "source_range": [job["start"], job["end"]],
            "model_frames": job["model_frames"], "seed": job["seed"]}


def verify_packet(root, packet_path, approval_path=None, reviewer=None):
    packet_file = local_file(root, packet_path)
    packet = read_json(packet_file)
    if packet.get("schema") != 1 or not packet.get("assets"):
        raise ValueError("Unsupported/empty packet")
    roles = [x["role"] for x in packet["assets"]]
    if roles.count("job") != 1 or roles.count("profile") != 1:
        raise ValueError("Packet requires one job and one profile")
    for row in packet["assets"]:
        if digest(local_file(root, row["path"])) != row["sha256"]:
            raise ValueError(f"Asset changed: {row['role']} {row['path']}")
    job_path = next(x["path"] for x in packet["assets"] if x["role"] == "job")
    profile_path = next(x["path"] for x in packet["assets"] if x["role"] == "profile")
    if freeze(root, job_path, profile_path) != packet:
        raise ValueError("Packet metadata/order differs from frozen job")
    if approval_path:
        if not reviewer:
            raise ValueError("Specify the reviewer expected by the active project protocol")
        approval = read_json(local_file(root, approval_path))
        if approval.get("approved") is not True or approval.get("reviewer") != reviewer:
            raise ValueError("Approval absent, withdrawn, or reviewer mismatch")
        if approval.get("request_sha256") != digest(packet_file):
            raise ValueError("Approval does not bind this exact request")
        if approval.get("job_id") != packet["job_id"]:
            raise ValueError("Approval job mismatch")
    return {"technical_validation": "PASS", "job_id": packet["job_id"],
            "approval_checked": bool(approval_path),
            "visual_approval": "not_assessed",
            "warning": "Hashes do not authenticate the human signer; consult the real approval source."}


def validate_ledger(root, ledger):
    start, end = ledger["start"], ledger["end"]
    if type(start) is not int or type(end) is not int or start < 0 or end <= start:
        raise ValueError("Invalid ledger range")
    fps = ledger["fps"]
    if not isinstance(fps, list) or len(fps) != 2:
        raise ValueError("fps must be [numerator, denominator]")
    for v in fps:
        positive_int(v, "fps component")
    rows = ledger["frames"]
    if [x["frame"] for x in rows] != list(range(start, end)):
        raise ValueError("Ledger has holes, duplicates, out-of-order or extra frames")
    hashes = {}
    for row in rows:
        kind = row["kind"]
        if kind not in ("generated", "copy", "native_layer"):
            raise ValueError("No placeholders or unknown asset kinds in final ledger")
        if row.get("selected") is not True:
            raise ValueError("Final rows must be explicitly selected")
        if type(row["asset_frame"]) is not int or row["asset_frame"] < 0:
            raise ValueError("Invalid asset-relative frame")
        if type(row["sr"]) is not bool:
            raise ValueError("sr must be a boolean")
        if row["sr"] and kind != "generated":
            raise ValueError("Copy/native layers must not pass through SR")
        path = row["path"]
        if path not in hashes:
            hashes[path] = digest(local_file(root, path))
        if hashes[path] != row["sha256"]:
            raise ValueError(f"Selected asset changed: {path}")
    return {"technical_validation": "PASS", "frames": end - start,
            "fps": fps, "unique_assets": len(hashes),
            "media_decode": "not_performed", "visual_approval": "not_assessed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("map")
    m.add_argument("--source-frames", type=int, required=True)
    m.add_argument("--model-frames", type=int, required=True)
    m.add_argument("--out")
    f = sub.add_parser("freeze")
    f.add_argument("--root", required=True)
    f.add_argument("--job", required=True)
    f.add_argument("--profile", required=True)
    f.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--root", required=True)
    v.add_argument("--packet", required=True)
    v.add_argument("--approval")
    v.add_argument("--reviewer")
    l = sub.add_parser("ledger")
    l.add_argument("--root", required=True)
    l.add_argument("--file", required=True)
    a = parser.parse_args()
    try:
        if a.command == "map":
            emit({"model_to_source": frame_map(a.source_frames, a.model_frames),
                  "native_to_model": frame_map(a.model_frames, a.source_frames)}, a.out)
        elif a.command == "freeze":
            emit(freeze(a.root, a.job, a.profile), a.out)
        elif a.command == "verify":
            emit(verify_packet(a.root, a.packet, a.approval, a.reviewer))
        else:
            emit(validate_ledger(a.root, read_json(a.file)))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Validation failed: {exc}\n")


if __name__ == "__main__":
    main()
