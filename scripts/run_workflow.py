"""workflows-api/ のワークフローの値を差し替えて実行し、出力を runs/ に取ってくる。

使い方:
  python3 scripts/run_workflow.py I_T2I --set "Positive.text=1girl, solo" --count 4
  python3 scripts/run_workflow.py I_Upscaler --image ./元の画像.png --set "KSampler.denoise=0.3"

--set "ノード.入力=値"
  ノードはノードの名前（画面のタイトル）、ノードの種類（class_type）、または #ID で指す。
  同じ名前のノードが二つ以上あるときはエラーになるので、#ID で指す。
  値は JSON として読めれば JSON（数値、true/false など）、読めなければ文字列になる。
--count N   N 回実行する。シードを --set で指定していなければ、毎回ランダムにする
--image P   P をアップロードして LoadImage に入れる（LoadImage が二つ以上なら --set で指す）
--no-eagle  Eagle Feeder のノードを外して実行する（試し撃ちで Eagle に送らない）
--dry-run   差し替えと検証だけして、送らない
"""

import argparse
import json
import mimetypes
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_workflows import check, fetch_object_info  # noqa: E402

BASE = os.environ.get("COMFYUI_URL", "http://localhost:8188")
ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "workflows-api"
RUNS_DIR = ROOT / "runs"
SEED_INPUTS = ("seed", "noise_seed")


def request_json(path, data=None):
    req = urllib.request.Request(BASE + path)
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"ComfyUI がエラーを返した（{e.code}）:\n{format_error(body)}")


def format_error(body):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body
    lines = [data.get("error", {}).get("message", "")]
    for node_id, err in (data.get("node_errors") or {}).items():
        for e in err.get("errors", []):
            lines.append(f"  #{node_id} {err.get('class_type')}: {e.get('message')} {e.get('details', '')}")
    return "\n".join(line for line in lines if line)


def find_nodes(prompt, ref):
    if ref.startswith("#"):
        return [ref[1:]] if ref[1:] in prompt else []
    by_title = [i for i, n in prompt.items() if n.get("_meta", {}).get("title") == ref]
    return by_title or [i for i, n in prompt.items() if n.get("class_type") == ref]


def parse_value(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def apply_set(prompt, spec):
    target, sep, value = spec.partition("=")
    ref, dot, name = target.rpartition(".")
    if not sep or not dot:
        raise SystemExit(f"--set の書き方が違う: {spec}（「ノード.入力=値」）")
    ids = find_nodes(prompt, ref)
    if not ids:
        raise SystemExit(f"ノード {ref} が見つからない")
    if len(ids) > 1:
        listed = ", ".join(f"#{i}" for i in ids)
        raise SystemExit(f"{ref} という名前のノードが複数ある（{listed}）。#ID で指す")
    node = prompt[ids[0]]
    if name not in node["inputs"]:
        raise SystemExit(f"#{ids[0]} {node['class_type']} に入力 {name} がない（あるのは {', '.join(node['inputs'])}）")
    if isinstance(node["inputs"][name], list):
        raise SystemExit(f"#{ids[0]} の {name} は別のノードからつながっているので、値を入れられない")
    node["inputs"][name] = parse_value(value)
    return ids[0], name


def upload_image(path):
    path = Path(path)
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + path.read_bytes() + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(BASE + "/upload/image", data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req) as res:
        info = json.load(res)
    return f"{info['subfolder']}/{info['name']}" if info.get("subfolder") else info["name"]


def drop_eagle(prompt):
    for node_id in [i for i, n in prompt.items() if str(n.get("class_type", "")).startswith("EagleFeeder")]:
        del prompt[node_id]


def wait_for(prompt_id):
    started = time.time()
    last = None
    while True:
        history = request_json(f"/history/{prompt_id}").get(prompt_id)
        if history and history.get("status", {}).get("completed") is not None:
            if history["status"].get("status_str") == "error":
                for kind, msg in history["status"].get("messages", []):
                    if kind == "execution_error":
                        raise SystemExit(
                            f"実行に失敗した: #{msg.get('node_id')} {msg.get('node_type')}: {msg.get('exception_message')}"
                        )
                raise SystemExit("実行に失敗した")
            if history["status"].get("completed"):
                return history
        queue = request_json("/queue")
        state = "実行中" if any(item[1] == prompt_id for item in queue["queue_running"]) else "待ち"
        if state != last:
            print(f"  {state}…")
            last = state
        time.sleep(2)
        if time.time() - started > 3600:
            raise SystemExit("一時間たっても終わらないので待つのをやめた")


def download_outputs(history, out_dir):
    saved = []
    for node_id, output in history.get("outputs", {}).items():
        for item in output.get("images", []) + output.get("gifs", []):
            query = urllib.parse.urlencode(
                {"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": item.get("type", "output")}
            )
            with urllib.request.urlopen(f"{BASE}/view?{query}") as res:
                dest = out_dir / f"{node_id.replace(':', '-')}_{item['filename']}"
                dest.write_bytes(res.read())
                saved.append(dest)
    return saved


def main():
    parser = argparse.ArgumentParser(description="ワークフローを実行して出力を取ってくる")
    parser.add_argument("workflow", help="workflows-api/ のファイル名（.json は省略可）かパス")
    parser.add_argument("--set", action="append", default=[], metavar="ノード.入力=値")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--image")
    parser.add_argument("--no-eagle", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = Path(args.workflow)
    if not path.is_file():
        path = API_DIR / (args.workflow if args.workflow.endswith(".json") else args.workflow + ".json")
    base_prompt = json.loads(path.read_text(encoding="utf-8"))

    if args.image:
        loaders = find_nodes(base_prompt, "LoadImage")
        if len(loaders) != 1:
            raise SystemExit("LoadImage が一つではないので --image は使えない。アップロード後の名前を --set で入れる")
        if args.dry_run:
            # 送らないときはアップロードもしない。検証は ComfyUI にある画像の一覧と比べるので、ここでは飛ばす
            name = Path(args.image).name
            print(f"アップロードする予定: {name} → #{loaders[0]}")
        else:
            name = upload_image(args.image)
            print(f"アップロード: {name} → #{loaders[0]}")
        base_prompt[loaders[0]]["inputs"]["image"] = name

    fixed_seeds = set()
    for spec in args.set:
        node_id, name = apply_set(base_prompt, spec)
        if name in SEED_INPUTS:
            fixed_seeds.add((node_id, name))
    if args.no_eagle:
        drop_eagle(base_prompt)

    problems = check(base_prompt, fetch_object_info())
    if args.image and args.dry_run:
        problems = [p for p in problems if not p.startswith(f"#{loaders[0]} LoadImage: image ")]
    if problems:
        print("検証で問題が見つかったので送らない:")
        for p in problems:
            print(f"  {p}")
        sys.exit(1)

    seed_targets = [
        (i, k)
        for i, n in base_prompt.items()
        for k in SEED_INPUTS
        if isinstance(n["inputs"].get(k), int) and (i, k) not in fixed_seeds
    ]
    if args.dry_run:
        print(f"検証は通った（ランダムにするシード: {', '.join(f'#{i}.{k}' for i, k in seed_targets) or 'なし'}）")
        return

    out_dir = RUNS_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{path.stem}"
    out_dir.mkdir(parents=True)
    client_id = uuid.uuid4().hex
    for run in range(1, args.count + 1):
        prompt = json.loads(json.dumps(base_prompt))
        seeds = {}
        for i, k in seed_targets:
            prompt[i]["inputs"][k] = seeds[f"#{i}.{k}"] = random.randint(0, 2**50)
        result = request_json("/prompt", {"prompt": prompt, "client_id": client_id})
        print(f"[{run}/{args.count}] 送った（prompt_id {result['prompt_id']}）" + (f" シード {seeds}" if seeds else ""))
        history = wait_for(result["prompt_id"])
        for dest in download_outputs(history, out_dir):
            print(f"  保存: {dest.relative_to(ROOT)}")
        (out_dir / f"{run:03}_prompt.json").write_text(json.dumps(prompt, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
