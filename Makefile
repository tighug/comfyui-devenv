download:
	git clone git@github.com:Comfy-Org/ComfyUI.git

link:
	ln -sr ./workflows ./ComfyUI/user/default/workflows
	ln -sr ./subgraphs ./ComfyUI/user/default/subgraphs

setup:
	python3 ./scripts/setup.py


start:
	python3 ./scripts/launch.py
