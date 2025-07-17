import asyncio
import logging
import os
import sys
from pathlib import Path

from temporalio.client import Client
from temporalio.worker import Worker

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from workflows import ProxyWorkflow, AnalysisWorkflow
from workflows.activities import AnalysisActivities


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
    activities = AnalysisActivities(output_dir=output_dir)

    # ワーカーの作成と起動
    worker = Worker(
        client,
        task_queue="analysis-task-queue",
        workflows=[ProxyWorkflow, AnalysisWorkflow],
        activities=[
            activities.process_analysis_data,
            activities.save_results,
        ],
    )

    logging.info("Starting worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
