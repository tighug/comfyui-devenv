"""export_api_in_browser.js が書き出した API 形式を workflows-api/ に取ってくる。

使い方: python3 scripts/pull_api_exports.py
ComfyUI の user/default/claude_export/ にあるファイルを取ってきて、取ったものは ComfyUI 側から消す。
"""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("COMFYUI_URL", "http://localhost:8188")
EXPORT_DIR = "claude_export"
API_DIR = Path(__file__).resolve().parent.parent / "workflows-api"


def userdata_url(name):
    return f"{BASE}/api/userdata/" + urllib.parse.quote(f"{EXPORT_DIR}/{name}", safe="")


def main():
    with urllib.request.urlopen(f"{BASE}/api/userdata?dir={EXPORT_DIR}") as res:
        names = json.load(res)
    if not names:
        print(f"{EXPORT_DIR} が空です。先に export_api_in_browser.js をブラウザで実行してください")
        return
    API_DIR.mkdir(exist_ok=True)
    for name in names:
        with urllib.request.urlopen(userdata_url(name)) as res:
            (API_DIR / name).write_bytes(res.read())
        urllib.request.urlopen(urllib.request.Request(userdata_url(name), method="DELETE"))
        print(f"取得  {name}")


if __name__ == "__main__":
    main()
