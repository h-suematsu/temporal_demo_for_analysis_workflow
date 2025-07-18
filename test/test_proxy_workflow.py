import asyncio
import uuid
from datetime import timedelta

import pytest
from temporalio.client import WorkflowExecutionStatus
from temporalio.service import RPCError

from workflows.analysis_workflow import AnalysisWorkflow
from workflows.models import AnalysisType, ProxyWorkflowInput
from workflows.proxy_workflow import ProxyWorkflow


async def wait_for_workflow(client, workflow_id, max_retries=5, retry_interval=0.5):
    """ワークフローが起動されるまで待機する"""
    for i in range(max_retries):
        try:
            handle = client.get_workflow_handle(workflow_id)
            status = await handle.describe()
            return status
        except RPCError:
            if i == max_retries - 1:
                raise
            await asyncio.sleep(retry_interval)
    raise RuntimeError("Workflow not found after maximum retries")


@pytest.mark.workflows([ProxyWorkflow, AnalysisWorkflow])
@pytest.mark.asyncio
async def test_proxy_workflow_basic(worker_info):
    """ProxyWorkflowの基本機能テスト"""
    client = worker_info["client"]

    # テスト用のペイロード
    job_id = str(uuid.uuid4())
    tenant_id = "test-tenant"
    payload = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "analysis_type": "type_a",
        "data": {"value": 42},
    }

    # ワークフローIDを作成
    analysis_workflow_id = f"analysis-{tenant_id}-{job_id}"

    # ProxyWorkflowを実行
    proxy_workflow_id = f"proxy-{uuid.uuid4()}"
    proxy_handle = await client.start_workflow(
        ProxyWorkflow.run,
        ProxyWorkflowInput(payload=payload),
        id=proxy_workflow_id,
        task_queue="test-task-queue",
        execution_timeout=timedelta(minutes=5),
    )

    # ProxyWorkflowが完了するのを待つ
    await proxy_handle.result()

    # AnalysisWorkflowが起動されたことを確認
    # Signal-with-Startパターンで自動的に起動される
    try:
        # ワークフローが存在するか確認、必要に応じてリトライ
        status = await wait_for_workflow(client, analysis_workflow_id)
        assert status.status == WorkflowExecutionStatus.RUNNING

        # すべてのシグナルが揃っていないため、ワークフローは実行中の状態
        # タイムアウトなしでresultを呼び出すとブロックされるのでdescribe()を使用
    except Exception as e:
        pytest.fail(f"AnalysisWorkflowが起動されませんでした: {e!s}")


@pytest.mark.workflows([ProxyWorkflow, AnalysisWorkflow])
@pytest.mark.asyncio
async def test_proxy_workflow_invalid_payload(worker_info):
    """無効なペイロードを処理する場合のテスト"""
    client = worker_info["client"]

    # 無効なペイロード(必須フィールドが欠けている)
    invalid_payload = {
        "data": {"value": 42}
        # job_id、tenant_id、analysis_typeが欠けている
    }

    # ProxyWorkflowを実行
    proxy_workflow_id = f"proxy-invalid-{uuid.uuid4()}"
    proxy_handle = await client.start_workflow(
        ProxyWorkflow.run,
        ProxyWorkflowInput(payload=invalid_payload),
        id=proxy_workflow_id,
        task_queue="test-task-queue",
        execution_timeout=timedelta(minutes=5),
    )

    # エラーが発生することを確認
    with pytest.raises(Exception, match=".*failed.*"):
        await proxy_handle.result()
    # 正しく失敗すればテストは通過


@pytest.mark.workflows([ProxyWorkflow, AnalysisWorkflow])
@pytest.mark.asyncio
async def test_proxy_workflow_all_analysis_types(worker_info):
    """すべての有効な解析タイプを処理する場合のテスト"""
    client = worker_info["client"]

    for analysis_type in AnalysisType:
        # 各解析タイプでのテスト
        job_id = str(uuid.uuid4())
        tenant_id = "test-tenant"
        payload = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "analysis_type": analysis_type.value,
            "data": {"value": 42},
        }

        # ProxyWorkflowを実行
        proxy_workflow_id = f"proxy-{analysis_type.value}-{uuid.uuid4()}"
        proxy_handle = await client.start_workflow(
            ProxyWorkflow.run,
            ProxyWorkflowInput(payload=payload),
            id=proxy_workflow_id,
            task_queue="test-task-queue",
            execution_timeout=timedelta(minutes=5),
        )

        # ワークフローが正常に完了することを確認
        await proxy_handle.result()

        # AnalysisWorkflowが起動されていることを確認
        analysis_workflow_id = f"analysis-{tenant_id}-{job_id}"
        try:
            status = await wait_for_workflow(client, analysis_workflow_id)
            assert status.status == WorkflowExecutionStatus.RUNNING
        except Exception as e:
            pytest.fail(
                f"{analysis_type.value}の場合、AnalysisWorkflowが起動されませんでした: {e!s}"
            )


@pytest.mark.workflows([ProxyWorkflow, AnalysisWorkflow])
@pytest.mark.asyncio
async def test_proxy_workflow_invalid_analysis_type(worker_info):
    """無効な解析タイプを処理する場合のテスト"""
    client = worker_info["client"]

    # 無効な解析タイプを含むペイロード
    invalid_type_payload = {
        "job_id": str(uuid.uuid4()),
        "tenant_id": "test-tenant",
        "analysis_type": "invalid_type",  # 無効な解析タイプ
        "data": {"value": 42},
    }

    # ProxyWorkflowを実行
    proxy_workflow_id = f"proxy-invalid-type-{uuid.uuid4()}"
    proxy_handle = await client.start_workflow(
        ProxyWorkflow.run,
        ProxyWorkflowInput(payload=invalid_type_payload),
        id=proxy_workflow_id,
        task_queue="test-task-queue",
        execution_timeout=timedelta(minutes=5),
    )

    # エラーが発生することを確認
    with pytest.raises(Exception, match=".*failed.*"):
        await proxy_handle.result()
    # 正しく失敗すればテストは通過
