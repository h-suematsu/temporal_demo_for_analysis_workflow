# ローカル環境でのセットアップと実行

このドキュメントでは、Temporalワークフローをローカル環境でセットアップして実行する方法を説明します。

## 前提条件

- Python 3.7以上
- Temporalサーバー（ローカルまたはリモート）

## 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

## 2. Temporalサーバーの起動

ローカルでTemporalサーバーを実行するには、以下のコマンドを使用します：

```bash
# Temporal CLIをインストールしていない場合
brew install temporalio/tap/temporal

# Temporalサーバーを開発モードで起動
temporal server start-dev
```

または、Docker Composeを使用する場合：

```bash
docker-compose up
```

## 3. ワーカーの起動

ワーカーを起動して、ワークフローとアクティビティを実行できるようにします：

```bash
python script/worker.py
```

## 4. ワークフローのトリガー

### ProxyWorkflowのトリガー

サンプルペイロードを使用してProxyWorkflowをトリガーします：

```bash
python script/trigger_proxy_workflow.py
```

または、カスタムペイロードファイルを指定：

```bash
python script/trigger_proxy_workflow.py script/sample_payload.json
```

### AnalysisWorkflowの直接トリガー

テスト目的でAnalysisWorkflowを直接トリガーし、シグナルを送信：

```bash
python script/trigger_analysis_workflow.py
```

## 5. 結果の確認

デフォルトでは、処理結果は`./output`ディレクトリに保存されます。出力ディレクトリを変更するには、環境変数`OUTPUT_DIR`を設定します：

```bash
OUTPUT_DIR=/path/to/output python script/worker.py
```

## 6. Temporalのウェブインターフェース

Temporalのウェブインターフェースにアクセスして、ワークフローの実行状況を確認できます：

```
http://localhost:8233
```