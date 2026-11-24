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

## フォルダ

| パス             | 中身                                                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------------------- |
| `workflows/`     | ワークフロー（UI 形式）。`make link` で `ComfyUI/user/default/workflows` にリンクする。画面の一覧に出る |
| `subgraphs/`     | 自作のサブグラフ。`ComfyUI/user/default/subgraphs` にリンクする                                         |
| `workflows-api/` | `workflows/` を API 形式に変換したもの。`/prompt` に送って実行するとき、スクリプトで直すとき用          |
| `scripts/`       | 起動、セットアップ、API 形式の書き出しと検証                                                            |

`workflows-api/` を `workflows/` の中に置くと、画面のワークフロー一覧に API 形式のファイルも並んでしまうので分けている。

## ワークフロー

画像（`I_`）と動画（`V_`、I2V）のワークフロー。
画像を出すワークフローでは、最後に WD14 Tagger でタグを付け、NudeNet でレーティングを判定して、タグ付きで Eagle に送る。

| 名前                 | 何をするか                                                                   | 入れるもの                       | 主なモデル・ノード                                          | 状態                                                                                  |
| -------------------- | ---------------------------------------------------------------------------- | -------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| I_T2I                | プロンプトから画像を作る。LoRA とトリガーワードは LoRA Manager で選ぶ        | プロンプト                       | WAI Illustrious v16、LoRA Manager                           | 動く                                                                                  |
| I_T2I_BG             | 背景用の I_T2I。人物を除くネガティブプロンプトで、横長（1600x1024）          | プロンプト                       | WAI Illustrious v16、LoRA Manager                           | 動く                                                                                  |
| I_CheckPoint_Catalog | 同じプロンプトを複数のチェックポイントで出し、モデル名のラベルを付けて並べる | プロンプト、参考画像             | Flanime IL v27、PlantMilk Walnut、NtrMIX IL XIII、ループ    | Flanime と NtrMIX がない。解像度プリセットがない                                      |
| I_Prompt_Catalog     | 候補のタグを一つずつ差し替えて出し、タグのラベルを付けて並べる               | プロンプト、比べたいタグ         | Flanime Illustrious XL v16、ループ                          | チェックポイントがない。解像度プリセットがない                                        |
| I_Depth              | 元の画像の深度を ControlNet に渡し、構図を保ったまま描き直す                 | 元の画像、プロンプト             | WAI Illustrious v16、Depth ControlNet（eugeoter）           | 動く                                                                                  |
| I_Detailer           | 乳首・下着・目を検出して、その部分だけ LoRA を当てて描き直す                 | 元の画像、プロンプト             | Impact Pack（SAM、Ultralytics、Detailer）、PlantMilk Walnut | 検出モデル 3 つと LoRA 3 つがない。Anything Everywhere が入っていない                 |
| I_Layer              | LayerDiffuse で背景が透明な画像を作る                                        | プロンプト（または元の画像）     | WAI Illustrious v16、LayerDiffuse                           | 動く                                                                                  |
| I_Tagger             | 画像からタグ（プロンプト）を取り出す                                         | 画像                             | WD14 Tagger                                                 | 動く                                                                                  |
| I_Upscaler           | 画像を拡大して描き直す。生成に使ったモデルとプロンプトを指定する             | 元の画像、プロンプト             | Ultimate SD Upscale、PlantMilk Walnut                       | アップスケールモデルがない。Ultimate SD Upscale と Anything Everywhere が入っていない |
| SeeThrough           | 一枚の画像を深度で前後のレイヤーに分けて、PSD で保存する                     | 画像                             | SeeThrough                                                  | 動く                                                                                  |
| I2V                  | 画像から動画を作る（Wan2.1）。幅と高さは 16 の倍数にする                     | 最初のフレームの画像、プロンプト | WanVideoWrapper、TeaCache、BlockSwap                        | WanVideoWrapper と Anything Everywhere が入っていない。解像度プリセットがない         |
| V_Loop               | 中身が空                                                                     |                                  |                                                             |                                                                                       |
| V_Upscaler           | 作りかけ（画像の読み込みだけ）                                               |                                  |                                                             |                                                                                       |

「動く」は、`make validate` でノードとモデルがそろっていると確かめたもの。入力画像（`LoadImage`）は実行のたびに差し替えるので、ないと出ても気にしなくてよい。
解像度プリセットは KJNodes の `custom_dimensions.json` に足していた自作の値（`7:4(1.75) - 1344x768` など）で、いまは初期状態に戻っている。

## Eagle のトークン

ワークフローの Eagle Feeder ノードの `eagle_token` は空にしておき、トークンは `.env` の `EAGLE_TOKEN` に書く（`.env.template` を参照）。
`make start`（`scripts/launch.py`）が `.env` を読んで ComfyUI に渡し、eagle-feeder はトークンの欄が空なら `EAGLE_TOKEN` を使う。
このリポジトリは公開しているので、ノードにトークンを入れたまま保存しない。

Eagle はホストの Windows で動かす。ComfyUI はコンテナの中なので、`eagle_host` は `http://localhost:41595` ではなく `http://host.docker.internal:41595` にする（コンテナの中の localhost はコンテナ自身を指す）。

## API 形式の書き出しと検証

`workflows/` を直したら、`workflows-api/` も作り直す。

1. ComfyUI の画面を開き、ブラウザの開発者ツールのコンソールで `scripts/export_api_in_browser.js` の中身を実行する。
   全部のワークフローを、画面が「実行」のときと同じ変換で API 形式にして、`ComfyUI/user/default/claude_export/` に書き出す。
   サブグラフや Anything Everywhere の接続も、実行時と同じに展開される
2. `make pull-api` で `workflows-api/` に取ってくる（ComfyUI 側の `claude_export/` は空になる）
3. `make validate` で確かめる。ノードの種類、必須の入力、接続の型、モデル名などの選択肢を、動いている ComfyUI の `/api/object_info` と突き合わせる

書き出すときに入っていないカスタムノードは、API 形式では種類の分からないノードになり、そのノードがつないでいた入力も抜ける。
足りないノードを入れてから 1 をやり直す。
モデルを入れたあとは、ComfyUI を再起動するか、画面で「Refresh」するとモデルの一覧が更新される。
