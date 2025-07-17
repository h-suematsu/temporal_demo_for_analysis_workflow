import logging
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError, CancelledError

with workflow.unsafe.imports_passed_through():
    from workflows.activities import AnalysisActivities
    from workflows.models import AnalysisRequest, AnalysisType, AnalysisWorkflowInput


@workflow.defn
class AnalysisWorkflow:
    """
    解析結果を処理し、データベースに保存するためのワークフロー
    """

    def __init__(self):
        self._pending_analysis_data: dict[AnalysisType, AnalysisRequest] = {}
        self._job_id: str | None = None
        self._tenant_id: str | None = None
        self._analysis_results: dict[str, Any] = {}

    @workflow.run
    async def run(self, workflow_input: AnalysisWorkflowInput) -> dict[str, Any]:
        """
        ワークフローの実行関数

        Args:
            input: ワークフロー入力データ

        Returns:
            Dict[str, Any]: 解析結果
        """
        self._job_id = workflow_input.job_id
        self._tenant_id = workflow_input.tenant_id

        logging.info(
            f"AnalysisWorkflow started for job_id={self._job_id}, tenant_id={self._tenant_id}"
        )

        try:
            # 必要なデータが揃うまで待機
            await self._wait_for_analysis_data()

            # 受信したデータを整形
            analysis_data = self._prepare_analysis_data()

            # データを処理するアクティビティを実行
            self._analysis_results = await self._process_analysis_data(analysis_data)

            # 結果を保存
            output_path = await self._save_results()

            logging.info(f"Analysis results saved to: {output_path}")

            return self._analysis_results

        except CancelledError:
            logging.info(f"AnalysisWorkflow cancelled for job_id={self._job_id}")
            raise
        except Exception as e:
            logging.error(f"Error in AnalysisWorkflow: {e!s}")
            raise ApplicationError(f"AnalysisWorkflow failed: {e!s}") from e

    async def _wait_for_analysis_data(self) -> None:
        """必要なすべての解析データが揃うまで待機する"""
        # 必要なすべての解析タイプのデータが揃うまで待機
        required_analysis_types = set(AnalysisType)

        # 必要なすべての解析タイプのデータが揃うまでループ
        while set(self._pending_analysis_data.keys()) != required_analysis_types:
            # シグナルを待機
            try:
                logging.info(
                    f"Waiting for analysis data. Received: {list(self._pending_analysis_data.keys())}"
                )
                logging.info(
                    f"Still waiting for: {list(required_analysis_types - set(self._pending_analysis_data.keys()))}"
                )

                # シグナルを待機(5秒タイムアウト)
                await workflow.wait_condition(
                    lambda: set(self._pending_analysis_data.keys())
                    == required_analysis_types,
                    timeout=timedelta(seconds=5),
                )
                break
            except TimeoutError:
                # タイムアウトした場合は、利用可能なデータで処理を継続
                logging.warning(
                    "Timeout waiting for all analysis data. Proceeding with available data."
                )
                break

    def _prepare_analysis_data(self) -> dict[str, dict[str, Any]]:
        """解析データをアクティビティ用に整形する"""
        analysis_data = {}
        for analysis_type, request in self._pending_analysis_data.items():
            # analysis_typeの型に応じた処理
            analysis_type_str = self._get_analysis_type_string(analysis_type)

            analysis_data[str(analysis_type)] = {
                "job_id": request.job_id,
                "tenant_id": request.tenant_id,
                "analysis_type": analysis_type_str,
                "data": getattr(request, "data", {}),
            }

        return analysis_data

    def _get_analysis_type_string(self, analysis_type: Any) -> str:
        """解析タイプを文字列化する"""
        # Enumの場合はvalueを取得、それ以外は文字列化
        result = (
            analysis_type.value
            if hasattr(analysis_type, "value")
            else str(analysis_type)
        )
        return result

    async def _process_analysis_data(
        self, analysis_data: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """アクティビティを呼び出して解析データを処理する"""
        return await workflow.execute_activity(
            AnalysisActivities.process_analysis_data,
            args=[self._job_id, self._tenant_id, analysis_data],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
            ),
        )

    async def _save_results(self) -> str:
        """結果を保存するアクティビティを実行する"""
        return await workflow.execute_activity(
            AnalysisActivities.save_results,
            args=[self._job_id, self._tenant_id, self._analysis_results],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
            ),
        )

    @workflow.signal
    def analysis_data_available(self, request: AnalysisRequest) -> None:
        """
        解析データが利用可能になったことを通知するシグナル

        Args:
            request: 解析リクエスト情報
        """
        if request.job_id != self._job_id or request.tenant_id != self._tenant_id:
            logging.warning(
                f"Received data for different job/tenant. Expected job_id={self._job_id}, tenant_id={self._tenant_id}, "
                f"got job_id={request.job_id}, tenant_id={request.tenant_id}"
            )
            return

        logging.info(f"Received analysis data for type: {request.analysis_type}")

        # Listの場合はtupleに変換してハッシュ可能にする
        if isinstance(request.analysis_type, list):
            analysis_type = tuple(request.analysis_type)
        else:
            analysis_type = request.analysis_type

        self._pending_analysis_data[analysis_type] = request
