import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from workflows.models import AnalysisRequest


class AnalysisActivities:
    """解析ワークフローで使用するアクティビティ"""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir

    @activity.defn
    async def process_analysis_data(
        self,
        job_id: str,
        tenant_id: str,
        analysis_data: dict[str, AnalysisRequest],
    ) -> dict[str, dict[str, Any]]:
        """
        解析データを処理するアクティビティ

        Args:
            job_id: ジョブID
            tenant_id: テナントID
            analysis_data: 解析データ(タイプごと)

        Returns:
            Dict[str, Any]: 処理結果
        """
        logging.info(
            f"Processing analysis data for job_id={job_id}, tenant_id={tenant_id}"
        )

        try:
            # 実際のアプリケーションでは、ここでデータ処理ロジックを実装
            # 例: データ変換、集計、結合などの処理
            return {
                analysis_type: request.data
                for analysis_type, request in analysis_data.items()
            }

        except Exception as e:
            logging.error(f"Error processing analysis data: {e!s}")
            raise ApplicationError(f"Analysis data processing failed: {e!s}") from e

    @activity.defn
    async def save_results(
        self, job_id: str, tenant_id: str, results: dict[str, dict[str, Any]]
    ) -> str:
        """
        処理結果をファイルに保存するアクティビティ

        Args:
            job_id: ジョブID
            tenant_id: テナントID
            results: 保存する結果データ

        Returns:
            str: 保存したファイルのパス
        """
        logging.info(f"Saving results for job_id={job_id}, tenant_id={tenant_id}")

        try:
            # 結果を整形
            final_result = {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "results": results,
                "completed_at": datetime.now(tz=UTC).isoformat(),
            }

            # ファイル名を生成
            filename = f"{tenant_id}_{job_id}_results.json"
            filepath = Path(self.output_dir) / filename

            # 結果をJSONファイルとして保存
            with filepath.open("w") as f:
                json.dump(final_result, f, indent=2)

            logging.info(f"Results saved to {filepath}")
            return str(filepath)

        except Exception as e:
            logging.error(f"Error saving results: {e!s}")
            raise ApplicationError(f"Results saving failed: {e!s}") from e
