# comfyui-devenv

ComfyUI を DevContainer で動かす環境と、自作のワークフロー。ワークフローの一覧、フォルダの役割、コマンドの使い方は README.md にあるので、作業前に読む。

## 動かし方

- ComfyUI はコンテナの中で動き、ホストの `http://localhost:8188` に転送されている
- ホストの Windows には Python がない。スクリプトはコンテナの中で動かす。コンテナは DevContainer のラベルで探す

  ```bash
  C=$(docker ps -q --filter "label=devcontainer.local_folder=c:\\win-workspace\\comfyui-devenv")
  MSYS_NO_PATHCONV=1 docker exec -w /workspaces/comfyui-devenv $C make validate
  ```

  Git Bash から `docker exec` するときは `MSYS_NO_PATHCONV=1` を付ける（付けないと `/workspaces/...` が Windows のパスに書き換わる）

- ComfyUI の起動と停止はユーザーがする。止まっていたら起動し直してもらう

## ワークフローを使う・直す

- 実行は `make run`（`scripts/run_workflow.py`）。試しに出すときは `--no-eagle` を付けて Eagle に送らない。出力は `runs/` に入るので、Read で見て確かめる
- ワークフローを直すときは `workflows/`（UI 形式、原本）を直し、README の手順で `workflows-api/` を書き出し直す。`workflows-api/` だけを直すと、次の書き出しで消える
- 新しく組むときは `/api/object_info` でノードの入力と選べる値を確かめてから書き、`make validate` か `--dry-run` で確かめる
- UI 形式の JSON は、モデル名のような文字列をそのまま置き換えるときだけ直接書き換える。`widgets_values` は順番で並んでいて、構造を変えると壊しやすい

## 公開リポジトリ

このリポジトリは公開している。トークン、API キー、LAN の IP をワークフローやスクリプトに書かない。Eagle のトークンは `.env` の `EAGLE_TOKEN` に置く。コミットの前に `git diff --cached` で確かめる。
