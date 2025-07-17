import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from workflows.models import AnalysisType


class AnalysisActivities:
    """解析ワークフローで使用するアクティビティ"""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        # 出力ディレクトリが存在しない場合は作成
        output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True)

    def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプを取得するヘルパーメソッド

        Returns:
            str: ISO形式のタイムスタンプ文字列
        """
        timestamp = None
        try:
            activity_info = activity.info()
            if hasattr(activity_info, "start_time"):
                timestamp = activity_info.start_time.isoformat()
            elif hasattr(activity_info, "started_time"):
                timestamp = activity_info.started_time.isoformat()
        except Exception:
            pass

        # タイムスタンプが取得できなかった場合は現在時刻を使用
        if not timestamp:
            timestamp = str(datetime.now(tz=UTC))

        return timestamp

    @activity.defn
    async def process_analysis_data(
        self,
        job_id: str,
        tenant_id: str,
        analysis_data: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
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

            results = {}
            for analysis_type_str, data in analysis_data.items():
                # 文字列の場合は AnalysisType に変換
                try:
                    if isinstance(analysis_type_str, str):
                        analysis_type = AnalysisType(analysis_type_str)
                    else:
                        # 文字列以外の場合はそのまま使用
                        analysis_type = analysis_type_str
                except ValueError:
                    # 無効なanalysis_type_strの場合はそのまま文字列として使用
                    analysis_type = analysis_type_str

                # ここでは単純な例として、データに処理済みフラグを追加
                processed_data = {
                    **data,
                    "processed": True,
                    "timestamp": self._get_current_timestamp(),
                }

                # analysis_typeがEnumの場合はvalueを使用、そうでない場合は文字列化
                key = (
                    analysis_type.value
                    if hasattr(analysis_type, "value")
                    else str(analysis_type)
                )
                results[key] = processed_data

            return results

        except Exception as e:
            logging.error(f"Error processing analysis data: {e!s}")
            raise ApplicationError(f"Analysis data processing failed: {e!s}") from e

    @activity.defn
    async def save_results(
        self, job_id: str, tenant_id: str, results: dict[str, Any]
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
                "completed_at": self._get_current_timestamp(),
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
