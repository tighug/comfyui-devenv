import os
from pathlib import Path

# --listen 0.0.0.0 はコンテナの外（ホストの localhost:8188）からつなぐため。
# ホストのどこまで開くかは docker-compose.yml の ports で決める（127.0.0.1 だけに出している）
command = ["python3", "./ComfyUI/main.py", "--listen", "0.0.0.0", "--enable-manager", "--reserve-vram", "0", "--cuda-device", "0", "--enable-cors-header"]

# .env の値を ComfyUI に環境変数で渡す（すでに設定されている変数はそのまま）
env = os.environ.copy()
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        key = key.strip()
        if sep and key and not key.startswith("#"):
            env.setdefault(key, value.strip())

# ComfyUI に置き換わる。docker stop の SIGTERM が ComfyUI に直接届き、すぐ止まる
os.execvpe(command[0], command, env)
