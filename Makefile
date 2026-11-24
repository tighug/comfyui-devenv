download:
	git clone git@github.com:Comfy-Org/ComfyUI.git

link:
	ln -sr ./workflows ./ComfyUI/user/default/workflows
	ln -sr ./subgraphs ./ComfyUI/user/default/subgraphs

setup:
	python3 ./scripts/setup.py


start:
	python3 ./scripts/launch.py

pull-api:
	python3 ./scripts/pull_api_exports.py

validate:
	python3 ./scripts/validate_workflows.py

# 例: make run WF=I_T2I ARGS='--set "Positive.text=1girl, solo" --count 4 --no-eagle'
run:
	python3 ./scripts/run_workflow.py $(WF) $(ARGS)
