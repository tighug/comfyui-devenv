"""API 形式のワークフローを、ComfyUI に送る前に確かめる。

使い方: python3 scripts/validate_workflows.py [ワークフロー.json ...]
引数がなければ workflows-api/ の全部を見る。
ノードの定義は動いている ComfyUI の /api/object_info から取る（COMFYUI_URL で変えられる）。
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

BASE = os.environ.get("COMFYUI_URL", "http://localhost:8188")
API_DIR = Path(__file__).resolve().parent.parent / "workflows-api"


def fetch_object_info():
    with urllib.request.urlopen(f"{BASE}/api/object_info") as res:
        return json.load(res)


def combo_options(spec):
    """入力定義から選べる値の一覧を取り出す（古い形式と COMBO の両方）。"""
    if not spec:
        return None
    kind = spec[0]
    if isinstance(kind, list):
        return kind
    if kind == "COMBO" and len(spec) > 1 and isinstance(spec[1].get("options"), list):
        return spec[1]["options"]
    return None


def check(prompt, object_info):
    problems = []
    for node_id, node in prompt.items():
        class_type = node.get("class_type")
        if not class_type:
            # 画面で書き出したとき、入っていないノードは種類が分からないまま残る
            problems.append(f"#{node_id}: 種類が分からないノード（書き出したときに ComfyUI に入っていなかった）")
            continue
        where = f"#{node_id} {class_type}"
        definition = object_info.get(class_type)
        if not definition:
            problems.append(f"{where}: ComfyUI に入っていないノード")
            continue
        required = definition.get("input", {}).get("required", {})
        optional = definition.get("input", {}).get("optional", {})
        inputs = node.get("inputs", {})
        for name in required:
            if name not in inputs:
                problems.append(f"{where}: 必須の入力 {name} がない")
        for name, value in inputs.items():
            spec = required.get(name) or optional.get(name)
            if isinstance(value, list):
                # ["ノードID", 出力の番号] は接続
                src_id, index = value
                src = prompt.get(src_id)
                if src is None:
                    problems.append(f"{where}: {name} のつなぎ先 #{src_id} がない")
                    continue
                src_def = object_info.get(src.get("class_type"))
                if not src_def:
                    continue
                outputs = src_def.get("output", [])
                if index >= len(outputs):
                    problems.append(f"{where}: {name} が #{src_id} の存在しない出力 {index} につながっている")
                    continue
                out_type = outputs[index]
                in_type = spec[0] if spec else None
                if (
                    isinstance(in_type, str)
                    and isinstance(out_type, str)
                    and "*" not in (in_type, out_type)
                    and out_type not in in_type.split(",")
                ):
                    problems.append(f"{where}: {name} は {in_type} だが、{out_type} がつながっている")
                continue
            options = combo_options(spec)
            if options is not None and value not in options:
                problems.append(f"{where}: {name} の値 {json.dumps(value, ensure_ascii=False)} が選択肢にない")
    return problems


def main():
    object_info = fetch_object_info()
    targets = [Path(p) for p in sys.argv[1:]] or sorted(API_DIR.glob("*.json"))
    failed = 0
    for path in targets:
        prompt = json.loads(path.read_text(encoding="utf-8"))
        problems = check(prompt, object_info) if prompt else ["ノードが一つもない"]
        label = f"{path.name}（{len(prompt)} ノード）"
        if problems:
            failed += 1
            print(f"NG  {label}")
            for p in problems:
                print(f"    {p}")
        else:
            print(f"OK  {label}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
