#!/bin/sh
# compose の comfyui コンテナが起動したときに動かす（docker-compose.yml の command）
set -e

git config --global --add safe.directory /workspaces/comfyui-devenv

# パッケージのボリュームが空のときだけ requirements.txt を入れる。
# 毎回入れると、Manager がカスタムノードのために上げたパッケージを固定の版に戻してしまう
marker=/usr/local/lib/python3.10/dist-packages/.requirements-installed
if [ ! -f "$marker" ]; then
    pip install -r requirements.txt
    touch "$marker"
fi

exec python3 ./scripts/launch.py
