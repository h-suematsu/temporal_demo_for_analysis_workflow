import asyncio
import logging
import os
import sys
from pathlib import Path

from temporalio.client import Client
from temporalio.worker import Worker

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from workflows.activities import AnalysisActivities
from workflows.proxy_activities import ProxyActivities
from workflows.analysis_workflow import AnalysisWorkflow
from workflows.proxy_workflow import ProxyWorkflow


async def main():
    """
    Temporalワーカーを起動する
    """
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Temporal接続設定
    client = await Client.connect("localhost:7233")

    # 出力ディレクトリの設定
    output_dir = os.environ.get("OUTPUT_DIR", "./output")
    output_path = Path(output_dir)
    if not output_path.exists():
        output_path.mkdir(parents=True)

    # アクティビティインスタンスの作成
    analysis_activities = AnalysisActivities(output_dir=output_dir)
    proxy_activities = ProxyActivities()

    # ワーカーの作成と起動
    worker = Worker(
        client,
        task_queue="analysis-task-queue",
        workflows=[ProxyWorkflow, AnalysisWorkflow],
        activities=[
            analysis_activities.process_analysis_data,
            analysis_activities.save_results,
            proxy_activities.signal_or_start_analysis_workflow,
        ],
    )

    logging.info("Starting worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
