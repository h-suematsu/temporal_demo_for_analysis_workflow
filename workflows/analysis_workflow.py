import logging
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError, CancelledError

with workflow.unsafe.imports_passed_through():
    from workflows.activities.analysis_activities import AnalysisActivities
    from workflows.models import AnalysisRequest, AnalysisType, AnalysisWorkflowInput


@workflow.defn
class AnalysisWorkflow:
    """
    解析結果を処理し、データベースに保存するためのワークフロー
    """

    def __init__(self):
        self._received_analysis_data: dict[str, AnalysisRequest] = {}
        self._job_id: str | None = None
        self._tenant_id: str | None = None

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
            expected_types = set(AnalysisType.__members__.values())
            await workflow.wait_condition(
                lambda: set(self._received_analysis_data.keys()) == expected_types,
                timeout=timedelta(minutes=10),  # 10分のタイムアウト
            )

            # データを処理するアクティビティを実行
            analysis_results = await workflow.execute_activity(
                AnalysisActivities.process_analysis_data,
                args=[self._job_id, self._tenant_id, self._received_analysis_data],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                ),
            )

            # 結果を保存
            output_path = await workflow.execute_activity(
                AnalysisActivities.save_results,
                args=[self._job_id, self._tenant_id, analysis_results],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                ),
            )
            logging.info(f"Analysis results saved to: {output_path}")
            return analysis_results

        except CancelledError:
            logging.info(f"AnalysisWorkflow cancelled for job_id={self._job_id}")
            raise
        except Exception as e:
            logging.error(f"Error in AnalysisWorkflow: {e!s}")
            raise ApplicationError(f"AnalysisWorkflow failed: {e!s}") from e

    @workflow.signal
    def analysis_data_available(self, request: AnalysisRequest) -> None:
        """
        解析データが利用可能になったことを通知するシグナル

        Args:
            request: 解析リクエスト情報
        """
        if (
            self._job_id is not None
            and self._tenant_id is not None
            and (request.job_id != self._job_id or request.tenant_id != self._tenant_id)
        ):
            logging.warning(
                f"Received data for different job/tenant. Expected job_id={self._job_id}, tenant_id={self._tenant_id}, "
                f"got job_id={request.job_id}, tenant_id={request.tenant_id}"
            )
            return

        if request.analysis_type not in AnalysisType.__members__.values():
            logging.error(f"Invalid analysis type: {request.analysis_type}")
            return

        self._received_analysis_data[request.analysis_type] = request
