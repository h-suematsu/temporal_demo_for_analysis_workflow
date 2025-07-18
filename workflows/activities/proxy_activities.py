import logging

from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import ApplicationError

from workflows.analysis_workflow import AnalysisWorkflow
from workflows.models import AnalysisRequest, AnalysisWorkflowInput


class ProxyActivities:
    """プロキシワークフローで使用するアクティビティ"""

    def __init__(self, client=None):
        """
        アクティビティの初期化

        Args:
            client: Temporalクライアントインスタンス。Noneの場合は自動的にlocalhostに接続する。
        """
        self.client = client

    @activity.defn
    async def signal_or_start_analysis_workflow(
        self, workflow_id: str, request: AnalysisRequest
    ) -> str:
        """
        Analysis Workflowが存在すれば信号を送り、存在しなければ起動して信号を送る

        Args:
            workflow_id: ワークフローID
            request: 解析リクエスト情報

        Returns:
            str: ワークフローの状態メッセージ
        """
        logging.info(f"Attempting to signal or start Analysis Workflow: {workflow_id}")

        try:
            if self.client is None:
                self.client = await Client.connect("localhost:7233")

            await self.client.start_workflow(
                AnalysisWorkflow.run,
                AnalysisWorkflowInput(
                    job_id=request.job_id, tenant_id=request.tenant_id
                ),
                id=workflow_id,
                task_queue=activity.info().task_queue,
                start_signal="analysis_data_available",
                start_signal_args=[request],
            )
            return f"Signal sent to existing Analysis Workflow: {workflow_id}"

        except Exception as e:
            logging.error(f"Error in signal_or_start_analysis_workflow: {e!s}")
            raise ApplicationError(f"Failed to signal or start workflow: {e!s}") from e
