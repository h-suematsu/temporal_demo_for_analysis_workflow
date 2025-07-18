import asyncio
import contextlib
import tempfile

import pytest
import pytest_asyncio
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflows.activities.analysis_activities import AnalysisActivities
from workflows.activities.proxy_activities import ProxyActivities


# pytest.mark.workflowsマーカーを登録
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "workflows: mark test to run with specific workflows"
    )


@pytest_asyncio.fixture
async def client():
    """Temporalクライアントのフィクスチャ"""
    # テスト用のワークフロー環境を作成
    async with await WorkflowEnvironment.start_local() as env:
        yield env.client


@pytest_asyncio.fixture
async def temp_dir():
    """一時的な出力ディレクトリを作成するフィクスチャ"""
    dir_path = tempfile.mkdtemp()
    yield dir_path

    # テスト後にディレクトリを削除(オプション)
    # shutil.rmtree(dir_path)


@pytest_asyncio.fixture
async def analysis_activities(temp_dir):
    """解析アクティビティインスタンスのフィクスチャ"""
    return AnalysisActivities(output_dir=temp_dir)


@pytest_asyncio.fixture
async def proxy_activities(client):
    """プロキシアクティビティインスタンスのフィクスチャ"""
    return ProxyActivities(client=client)


@pytest_asyncio.fixture
async def worker_info(client, analysis_activities, proxy_activities, request):
    """
    テスト用のワーカーを作成するフィクスチャ

    テスト関数のmark.workflowsパラメータからワークフローリストを取得
    例: @pytest.mark.workflows([ProxyWorkflow])
    """
    # テスト関数からワークフローリストを取得
    workflows = request.node.get_closest_marker("workflows")
    if not workflows:
        pytest.fail(
            "テストにworkflowsマーカーが設定されていません。@pytest.mark.workflows([...])を使用してください。"
        )

    workflows = workflows.args[0]

    # テスト用のワーカーを作成
    worker = Worker(
        client,
        task_queue="test-task-queue",
        workflows=workflows,
        activities=[
            analysis_activities.process_analysis_data,
            analysis_activities.save_results,
            proxy_activities.signal_or_start_analysis_workflow,
        ],
    )

    # ワーカーを非同期で起動
    worker_task = asyncio.create_task(worker.run())

    # テスト用の情報を返す
    yield {
        "worker": worker,
        "task": worker_task,
        "output_dir": analysis_activities.output_dir,
        "client": client,
    }

    # テスト後にワーカーをキャンセル
    worker_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await worker_task
