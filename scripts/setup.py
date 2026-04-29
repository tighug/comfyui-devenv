import subprocess
import sys
from pathlib import Path

custom_nodes = Path("ComfyUI/custom_nodes")

for node_dir in custom_nodes.iterdir():
    if not node_dir.is_dir():
        continue
    req = node_dir / "requirements.txt"
    if req.is_file():
        print(f"Installing requirements for {node_dir.name}...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req)],
            check=False,
        )