# ComfyUI DevEnv

## Usage

```bash
# Download ComfyUI
make download

# Setup
cd ComfyUI; \
uv venv; \
source .venv/bin/activate; \
uv add -r requirements.txt; \
uv sync

# Start
python main.py
```
