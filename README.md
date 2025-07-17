# ここは

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Temporal が解析 DB の脱 dbt(workflow 導入)の要件に合うかを検証する場

## 背景

現在 ML モデルによる複数の解析結果を dbt によって作成される複数のクエリ群によって加工・集約され解析 DB と呼ばれるデータベースに保存されています。

ML 解析結果(PubSub) -> BigQuery -> dbt クエリ -> BigQuery

ただ SQL で表現するにはあまりに複雑なクエリになっていることもあり、メンテナンス・監視ができていないのが現状です。

## Workflow に求める要件

- dbt のクエリ群を workflow の step に分解して IO を明確にすることで、テストを容易にする
- 数時間の間で解析された結果を丸ごとクエリするのではなく、解析処理ごとに workflow を実行させるようにしたい（バッチ処理よりはイベント処理に近い）
  - ロジックの簡素化を実現したい
- step 間の中間生成物はインメモリーに限定する
- workflow の最終生成物のみを DB あるいはファイル出力する
- 解析結果は PubSub の Topic に送信されるため、結果を push/pull のどちらかで取得する必要がある
  - workflow 開始時にはまだ出力が完了していない可能性があり、完了まで待機する必要がある
  - workflow の中で複数の解析結果を取得するが、同じ job_id の解析結果を取得する必要がある
- 20K events/min 程度の workflow run に耐えることができる耐久性とスケーラビリティ
- 品質
  - 各 step は単体テストによって品質が担保される
  - workflow はローカルで検証できる状態になっている
- 言語
  - Python を基本とする

## Workflow の構成

- PubSub の push event を受け取る用の Proxy Workflow
  - 検証では PubSub の容易は不要で、REST API 経由で worflow がトリガーされるところから再現したい
  - Proxy Workflow では PubSub のメッセージ（リクエスト body）から job_id, tenant_id, analysis_type などを取得し、Analysis Workflow に対して Signal を送信する
- 解析 DB のデータを生成するための Analysis Workflow
  - Analysis Workflow では analysis_type の Signal を元に必要なデータが揃ったら処理を開始するようにする
  - Analysis Workflow で生成された各データはファイルに出力され蓄積される
  - step は役割に応じて分割して実装すること（適宜共通化も行う）

## 環境構築

### 開発ツールのセットアップ

```bash
# プロジェクトのクローン
# git clone ...

# pre-commitとpre-pushフックのインストール
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type pre-push
```

詳細な開発ガイドは[CONTRIBUTING.md](CONTRIBUTING.md)を参照してください。

### 依存関係のセットアップ

```bash
# uv のインストール（必要な場合）
brew install uv

# 仮想環境の作成
uv venv

# 依存関係のインストール
uv sync --all-groups --extra dev
```

### Temporal サーバーのセットアップ

```bash
# Temporal CLI のインストール（必要な場合）
brew install temporalio/tap/temporal

# ローカルで Temporal サーバーを起動
temporal server start-dev
```

## ワークフローの実行

```bash
# 仮想環境の有効化
source .venv/bin/activate

# ワーカーの起動
uv run python -m script.worker

# ワークフローのトリガー
uv run python -m script.trigger_analysis_workflow
# または
uv run python -m script.trigger_proxy_workflow
```

## テストの実行

```bash
# 依存関係の同期
uv sync --all-groups --extra dev

# テストの実行
uv run pytest test/
```

## リントとフォーマット

```bash
# Ruff でリントチェック
uv run ruff check .

# 自動修正可能な問題を修正
uv run ruff check --fix .

# コードフォーマット
uv run ruff format .
```
