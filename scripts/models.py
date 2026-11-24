"""models/ に置くモデルを models.lock.json で管理する。

使い方:
  python3 scripts/models.py lock    今の models/ から models.lock.json を書き直す
  python3 scripts/models.py check   models.lock.json と models/ を比べる（足りないもの、載っていないもの）
  python3 scripts/models.py fetch   models.lock.json にあって models/ に無いものを Civitai から落とす

models.lock.json には、Civitai から落としたモデルの版の ID、置く場所、SHA256 を書く。
版は固定するので、fetch は作者が新しい版を出しても同じファイルを落とす。
Civitai の情報は、LoRA Manager がモデルの隣に置く .metadata.json から読む。
.metadata.json が無いか、Civitai のモデルでないファイルは "local" に名前だけ書く（fetch では落とせない）。
fetch には .env の CIVITAI_API_KEY を使う。
"""

import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
LOCK = ROOT / "models.lock.json"
# 管理するフォルダ。ほかのフォルダ（SeeThrough、text_encoders など）はノードや Hugging Face から入るので見ない
KINDS = ("checkpoints", "loras", "diffusion_models", "embeddings", "vae", "controlnet", "upscale_models")
EXTS = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf")


def model_files():
    for kind in KINDS:
        base = MODELS / kind
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix.lower() in EXTS and not p.name.endswith(".part"):
                yield p


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p):
    return p.relative_to(MODELS).as_posix()


def read_lock():
    if not LOCK.is_file():
        sys.exit("models.lock.json が無い。先に lock を実行する")
    return json.loads(LOCK.read_text(encoding="utf-8"))


def by_hash(digest):
    """SHA256 から Civitai の版を引く。Civitai に無ければ None"""
    req = urllib.request.Request(f"https://civitai.com/api/v1/model-versions/by-hash/{digest}",
                                 headers={"User-Agent": "comfyui-devenv"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def cmd_lock():
    old_lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.is_file() else {"civitai": [], "local": []}
    old = {m["path"]: m for m in old_lock["civitai"]}
    civitai, local = [], []
    for p in model_files():
        meta_path = p.with_suffix(".metadata.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        cv = meta.get("civitai") or {}
        digest = (meta.get("sha256") or "").lower()
        prev = old.get(rel(p))
        if prev and prev["size"] == p.stat().st_size:
            civitai.append(prev)  # 前に調べた結果をそのまま使う
            continue
        if not (meta.get("from_civitai") and cv.get("id") and cv.get("modelId")):
            if rel(p) in old_lock["local"] and digest:
                local.append(rel(p))  # 前に Civitai に無かったものは聞き直さない
                continue
            digest = digest or sha256(p)
            print(f"Civitai に問い合わせる: {rel(p)}", flush=True)
            cv = by_hash(digest) or {}
            if not cv.get("modelId"):
                local.append(rel(p))
                continue
        digest = digest or sha256(p)
        civitai.append({
            "path": rel(p),
            "model": (cv.get("model") or {}).get("name") or meta.get("model_name"),
            "version": cv.get("name"),
            "type": (cv.get("model") or {}).get("type"),
            "base": cv.get("baseModel") or meta.get("base_model"),
            "modelId": cv["modelId"],
            "versionId": cv["id"],
            "size": p.stat().st_size,
            "sha256": digest,
        })
    data = {"civitai": civitai, "local": local}
    LOCK.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"models.lock.json: Civitai {len(civitai)} 個、ほか {len(local)} 個")


def cmd_check():
    lock = read_lock()
    listed = {m["path"] for m in lock["civitai"]} | set(lock["local"])
    on_disk = {rel(p) for p in model_files()}
    missing = [m["path"] for m in lock["civitai"] if m["path"] not in on_disk]
    missing_local = [p for p in lock["local"] if p not in on_disk]
    extra = sorted(on_disk - listed)
    for title, items in (("models/ に無い（fetch で落とせる）", missing),
                         ("models/ に無い（Civitai のモデルでないので落とせない）", missing_local),
                         ("models.lock.json に載っていない（lock で足す）", extra)):
        if items:
            print(f"{title}: {len(items)} 個")
            for i in items:
                print(f"  {i}")
    if not (missing or missing_local or extra):
        print("models.lock.json と models/ は同じ")
    return 1 if (missing or missing_local or extra) else 0


def api_key():
    key = os.environ.get("CIVITAI_API_KEY")
    env = ROOT / ".env"
    if not key and env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() == "CIVITAI_API_KEY":
                key = v.strip()
    if not key:
        sys.exit("CIVITAI_API_KEY が無い（.env に書く）")
    return key


def cmd_fetch():
    lock = read_lock()
    todo = [m for m in lock["civitai"] if not (MODELS / m["path"]).is_file()]
    if not todo:
        print("落とすものは無い")
        return 0
    key = api_key()
    total = sum(m["size"] for m in todo)
    print(f"{len(todo)} 個、{total / 2**30:.1f} GB を落とす")
    failed = []
    for i, m in enumerate(todo, 1):
        dest = MODELS / m["path"]
        part = dest.with_name(dest.name + ".part")
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{i}/{len(todo)}] {m['path']} ({m['size'] / 2**20:.0f} MB)", flush=True)
        ok = False
        for _ in range(3):
            subprocess.run([
                "curl", "-sS", "-L", "--fail", "--retry", "3", "-C", "-",
                "-H", f"Authorization: Bearer {key}", "-o", str(part),
                f"https://civitai.com/api/download/models/{m['versionId']}",
            ])
            if part.is_file() and part.stat().st_size >= m["size"]:
                if sha256(part) == m["sha256"]:
                    part.rename(dest)
                    ok = True
                    break
                print("  SHA256 が合わないので落とし直す")
                part.unlink()
            elif not part.is_file():
                break  # 403（先行公開）や 404（消された）のときは繰り返しても同じ
        if not ok:
            failed.append(m)
            print(f"  失敗: https://civitai.com/models/{m['modelId']}?modelVersionId={m['versionId']}")
    if failed:
        print(f"\n失敗 {len(failed)} 個。ページを開いて、先行公開か、消されたかを確かめる")
        return 1
    print("\nすべて落とした")
    return 0


if __name__ == "__main__":
    cmds = {"lock": cmd_lock, "check": cmd_check, "fetch": cmd_fetch}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    sys.exit(cmds[sys.argv[1]]() or 0)
