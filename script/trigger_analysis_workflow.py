import asyncio
import logging
import sys
import uuid
from datetime import timedelta
from pathlib import Path

from temporalio.client import Client

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from workflows.analysis_workflow import AnalysisWorkflow, AnalysisWorkflowInput
from workflows.models import AnalysisRequest, AnalysisType


async def main():
    """
    AnalysisWorkflowをトリガーして、シグナルを送信する
    """
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # サンプルのジョブIDとテナントID
    job_id = str(uuid.uuid4())
    tenant_id = "tenant-001"

    logging.info(f"Using job_id: {job_id}, tenant_id: {tenant_id}")

    # Temporal接続設定
    client = await Client.connect("localhost:7233")

    # AnalysisWorkflowの実行
    workflow_id = f"analysis-{tenant_id}-{job_id}"
    handle = await client.start_workflow(
        AnalysisWorkflow.run,
        AnalysisWorkflowInput(job_id=job_id, tenant_id=tenant_id),
        id=workflow_id,
        task_queue="analysis-task-queue",
        execution_timeout=timedelta(hours=1),
    )

    logging.info(f"Started AnalysisWorkflow with ID: {workflow_id}")

    # 各解析タイプのシグナルを送信
    for analysis_type in [
        AnalysisType.TYPE_A,
        AnalysisType.TYPE_B,
        AnalysisType.TYPE_C,
    ]:
        request = AnalysisRequest(
            job_id=job_id, tenant_id=tenant_id, analysis_type=analysis_type
        )

        # シグナルを送信
        await handle.signal("analysis_data_available", request)
        logging.info(f"Sent signal for analysis_type: {analysis_type}")

        # シグナル間に少し待機(実際のアプリケーションでは不要かもしれない)
        await asyncio.sleep(1)

    # ワークフローの結果を待つ
    result = await handle.result()
    logging.info(f"AnalysisWorkflow completed with result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
