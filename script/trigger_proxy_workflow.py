import asyncio
import json
import logging
import sys
import uuid
from datetime import timedelta
from pathlib import Path

from temporalio.client import Client

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from workflows import ProxyWorkflow, ProxyWorkflowInput


async def main():
    """
    ProxyWorkflowをトリガーする
    """
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # コマンドライン引数からペイロードファイルを取得
    if len(sys.argv) > 1:
        payload_file = sys.argv[1]
        with Path(payload_file).open() as f:
            payload = json.load(f)
    else:
        # サンプルペイロードの作成
        job_id = str(uuid.uuid4())
        payload = {
            "job_id": job_id,
            "tenant_id": "tenant-001",
            "analysis_type": "type_a",
            "data": {"value": 42, "timestamp": "2023-07-17T12:34:56Z"},
        }
        logging.info(f"Using sample payload with job_id: {job_id}")

    # Temporal接続設定
    client = await Client.connect("localhost:7233")

    # ProxyWorkflowの実行
    workflow_id = f"proxy-{uuid.uuid4()}"
    handle = await client.start_workflow(
        ProxyWorkflow.run,
        ProxyWorkflowInput(payload=payload),
        id=workflow_id,
        task_queue="analysis-task-queue",
        execution_timeout=timedelta(minutes=5),
    )

    logging.info(f"Started ProxyWorkflow with ID: {workflow_id}")

    # ワークフローの結果を待つ(この場合はNone)
    result = await handle.result()
    logging.info(f"ProxyWorkflow completed: {result}")


if __name__ == "__main__":
    asyncio.run(main())
