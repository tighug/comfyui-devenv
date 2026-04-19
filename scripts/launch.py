import subprocess

command = ["python3", "./ComfyUI/main.py", "--enable-manager", "--reserve-vram", "0", "--cuda-device", "0"]

subprocess.run(command)
