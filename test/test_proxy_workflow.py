import uuid
from datetime import timedelta

import pytest
from temporalio.client import WorkflowExecutionStatus

from workflows import (
    ProxyWorkflow,
    AnalysisWorkflow,
    ProxyWorkflowInput,
    AnalysisWorkflowInput,
)


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

    # 関連するAnalysisWorkflowを先に起動
    analysis_workflow_id = f"analysis-{tenant_id}-{job_id}"
    analysis_handle = await client.start_workflow(
        AnalysisWorkflow.run,
        AnalysisWorkflowInput(job_id=job_id, tenant_id=tenant_id),
        id=analysis_workflow_id,
        task_queue="test-task-queue",
        execution_timeout=timedelta(minutes=5),
    )

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

    # AnalysisWorkflowが終了していないことを確認(すべてのシグナルが揃っていないため)
    # タイムアウトなしでresultを呼び出すとブロックされるので、
    # describe()を使用してワークフローの状態を確認
    workflow_status = await analysis_handle.describe()
    assert workflow_status.status == WorkflowExecutionStatus.RUNNING


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
