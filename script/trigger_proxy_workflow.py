import argparse
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

from workflows.models import AnalysisType
from workflows.proxy_workflow import ProxyWorkflow, ProxyWorkflowInput


def parse_args():
    parser = argparse.ArgumentParser(description="ProxyWorkflowをトリガーする")
    # ペイロードファイルかコマンドライン引数
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--file", help="ペイロードファイルのパス")
    # 個別パラメータ
    parser.add_argument("--job-id", help="ジョブID")
    parser.add_argument("--tenant-id", default="tenant-001", help="テナントID")
    parser.add_argument(
        "--analysis-type",
        choices=[t.value for t in AnalysisType],
        default="type_a",
        help="解析タイプ",
    )
    return parser.parse_args()


async def main():
    """
    ProxyWorkflowをトリガーする
    """
    # 引数の解析
    args = parse_args()

    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # ペイロードの作成
    if args.file:
        # ファイルからペイロードを取得
        with Path(args.file).open() as f:
            payload = json.load(f)
    else:
        # 個別パラメータからペイロードを作成
        job_id = args.job_id if args.job_id else str(uuid.uuid4())
        payload = {
            "job_id": job_id,
            "tenant_id": args.tenant_id,
            "analysis_type": args.analysis_type,
            "data": {"value": 42, "timestamp": "2023-07-17T12:34:56Z"},
        }
        logging.info(
            f"Using job_id: {job_id}, tenant_id: {args.tenant_id}, analysis_type: {args.analysis_type}"
        )

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
