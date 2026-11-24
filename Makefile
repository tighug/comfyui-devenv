download:
	git clone git@github.com:Comfy-Org/ComfyUI.git

link: link-models
	ln -sr ./workflows ./ComfyUI/user/default/workflows
	ln -sr ./subgraphs ./ComfyUI/user/default/subgraphs

link-models:
	@# モデルは clone の外の ./models に置く。clone したての ComfyUI/models は置き場所の目印のファイルしかないので消してリンクにする
	@if [ ! -L ./ComfyUI/models ]; then \
		if find ./ComfyUI/models -type f ! -name 'put_*_here' | grep -q .; then \
			echo "ComfyUI/models にモデルがあるので止めた。./models に移してからやり直す"; exit 1; \
		fi; \
		rm -r ./ComfyUI/models && ln -sr ./models ./ComfyUI/models; \
	fi

setup:
	python3 ./scripts/setup.py

# モデルの一覧（models.lock.json）。入れた・消したあとに lock して、コミットする
models-lock:
	python3 ./scripts/models.py lock

models-check:
	python3 ./scripts/models.py check

models-fetch:
	python3 ./scripts/models.py fetch


start:
	python3 ./scripts/launch.py

pull-api:
	python3 ./scripts/pull_api_exports.py

validate:
	python3 ./scripts/validate_workflows.py

# 例: make run WF=I_T2I ARGS='--set "Positive.text=1girl, solo" --count 4 --no-eagle'
run:
	python3 ./scripts/run_workflow.py $(WF) $(ARGS)
