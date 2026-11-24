import os
import subprocess
from pathlib import Path

command = ["python3", "./ComfyUI/main.py", "--enable-manager", "--reserve-vram", "0", "--cuda-device", "0", "--enable-cors-header"]

# .env の値を ComfyUI に環境変数で渡す（すでに設定されている変数はそのまま）
env = os.environ.copy()
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        key = key.strip()
        if sep and key and not key.startswith("#"):
            env.setdefault(key, value.strip())

subprocess.run(command, env=env)
