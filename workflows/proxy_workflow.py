import json
import logging
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from workflows.activities.proxy_activities import ProxyActivities

from workflows.models import AnalysisRequest, AnalysisType, ProxyWorkflowInput


@workflow.defn
class ProxyWorkflow:
    """
    PubSubのイベントを受け取り、Analysis Workflowにシグナルを送信するためのプロキシワークフロー
    """

    @workflow.run
    async def run(self, workflow_input: ProxyWorkflowInput) -> None:
        """
        ワークフローの実行関数
        Args:
            input: PubSubイベントのペイロード
        """
        logging.info(f"ProxyWorkflow started with payload: {workflow_input.payload}")

        try:
            # PubSubメッセージからリクエスト情報を抽出
            request = self._extract_request_from_payload(workflow_input.payload)

            # Analysis Workflowにシグナルを送信
            # シグナルのターゲットとなるワークフローのIDを作成
            # 同じjob_idとtenant_idの組み合わせに対して同じワークフローインスタンスを使用
            workflow_id = f"analysis-{request.tenant_id}-{request.job_id}"

            # Activityを使用してAnalysis Workflowのシグナル送信または起動を行う
            # Activityの中でクライアントを生成してワークフローへのシグナル送信または起動を実行
            result = await workflow.execute_activity(
                ProxyActivities.signal_or_start_analysis_workflow,
                args=[workflow_id, request],
                start_to_close_timeout=timedelta(30),
            )
            logging.info(result)

            logging.info(f"Signal sent to Analysis Workflow: {workflow_id}")

        except Exception as e:
            logging.error(f"Error in ProxyWorkflow: {e!s}")
            raise ApplicationError(f"ProxyWorkflow failed: {e!s}") from e

    def _extract_request_from_payload(self, payload: dict[str, Any]) -> AnalysisRequest:
        """
        PubSubペイロードからリクエスト情報を抽出する

        Args:
            payload: PubSubメッセージのペイロード

        Returns:
            AnalysisRequest: 抽出されたリクエスト情報
        """
        try:
            # payloadがJSON文字列の場合はデコード
            if isinstance(payload, str):
                payload = json.loads(payload)

            # 必須フィールドの存在確認
            if "job_id" not in payload:
                raise ValueError("job_id is missing in payload")

            if "tenant_id" not in payload:
                raise ValueError("tenant_id is missing in payload")

            if "analysis_type" not in payload:
                raise ValueError("analysis_type is missing in payload")

            # analysis_typeが有効な値であることを確認
            analysis_type_str = payload["analysis_type"]
            try:
                analysis_type = AnalysisType(analysis_type_str)
            except ValueError as ve:
                raise ValueError(f"Invalid analysis_type: {analysis_type_str}") from ve

            return AnalysisRequest(
                job_id=payload["job_id"],
                tenant_id=payload["tenant_id"],
                analysis_type=analysis_type,
            )

        except Exception as e:
            logging.error(f"Failed to extract request from payload: {e!s}")
            raise ApplicationError(f"Invalid payload format: {e!s}") from e
