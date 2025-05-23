download:
	git clone https://github.com/comfyanonymous/ComfyUI

start:
	python3 ./scripts/launch.py

exp-workflow:
	cp -r ./ComfyUI/my_workflows ./

sync-civitai:
	python3 ./scripts/sync_civitai.py
