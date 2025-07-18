import uuid
from unittest.mock import MagicMock, patch

import pytest

from workflows.activities.proxy_activities import ProxyActivities
from workflows.analysis_workflow import AnalysisWorkflow
from workflows.models import AnalysisRequest, AnalysisType


@pytest.mark.workflows([AnalysisWorkflow])
@pytest.mark.asyncio
async def test_signal_or_start_analysis_workflow_new_workflow(worker_info):
    """新しいワークフローを起動するケースのテスト"""
    # テスト用クライアントを取得
    client = worker_info["client"]

    # テスト用のリクエストデータを作成
    job_id = str(uuid.uuid4())
    tenant_id = "test-tenant"
    workflow_id = f"analysis-test-{tenant_id}-{job_id}"
    request = AnalysisRequest(
        job_id=job_id,
        tenant_id=tenant_id,
        analysis_type=AnalysisType.TYPE_A,
        data={"value": 42, "source": "test"},
    )

    # モックを設定
    mock_activity_info = MagicMock()
    mock_activity_info.task_queue = "test-task-queue"

    # アクティビティをインスタンス化(テスト用クライアントを渡す)
    proxy_activities = ProxyActivities(client=client)

    # モックを適用
    with patch("temporalio.activity.info", return_value=mock_activity_info):
        # アクティビティを実行
        result = await proxy_activities.signal_or_start_analysis_workflow(
            workflow_id, request
        )

    # 返り値を検証
    assert "Signal sent to existing Analysis Workflow" in result
    assert workflow_id in result

    # ワークフローが起動されたことを確認
    handle = client.get_workflow_handle(workflow_id)
    # 状態確認は省略、テスト後のクリーンアップ
    await handle.cancel()


@pytest.mark.workflows([AnalysisWorkflow])
@pytest.mark.asyncio
async def test_signal_or_start_analysis_workflow_all_types(worker_info):
    """異なる解析タイプでテスト"""
    # テスト用クライアントを取得
    client = worker_info["client"]

    # 各解析タイプでテスト
    for analysis_type in AnalysisType:
        # テスト用のリクエストデータを作成
        job_id = str(uuid.uuid4())
        tenant_id = "test-tenant"
        workflow_id = f"analysis-{analysis_type.value}-{job_id}"
        request = AnalysisRequest(
            job_id=job_id,
            tenant_id=tenant_id,
            analysis_type=analysis_type,
            data={"value": 42, "source": "test"},
        )

        # モックを設定
        mock_activity_info = MagicMock()
        mock_activity_info.task_queue = "test-task-queue"

        # アクティビティをインスタンス化(テスト用クライアントを渡す)
        proxy_activities = ProxyActivities(client=client)

        # モックを適用
        with patch("temporalio.activity.info", return_value=mock_activity_info):
            # アクティビティを実行
            result = await proxy_activities.signal_or_start_analysis_workflow(
                workflow_id, request
            )

        # 返り値を検証
        assert "Signal sent to existing Analysis Workflow" in result
        assert workflow_id in result

        # ワークフローが起動されたことを確認
        handle = client.get_workflow_handle(workflow_id)
        # 状態確認は省略、テスト後のクリーンアップ
        await handle.cancel()
