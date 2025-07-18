import json
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from temporalio import activity
from temporalio.exceptions import ApplicationError

from workflows.activities import AnalysisActivities
from workflows.models import AnalysisType


class TestAnalysisActivities:
    """AnalysisActivitiesのテストクラス"""

    @pytest.fixture
    def temp_output_dir(self):
        """一時的な出力ディレクトリを作成するフィクスチャ"""
        temp_dir = tempfile.mkdtemp()
        return temp_dir

        # テスト後にディレクトリを削除(オプション)
        # shutil.rmtree(temp_dir)

    @pytest.fixture
    def activities(self, temp_output_dir):
        """アクティビティインスタンスのフィクスチャ"""
        return AnalysisActivities(output_dir=temp_output_dir)

    @pytest.mark.asyncio
    async def test_process_analysis_data(self, activities, monkeypatch):
        """process_analysis_dataアクティビティのテスト"""

        # activityInfoをモック化
        class MockActivityInfo:
            def __init__(self):
                self.start_time = datetime.now(tz=UTC)

        monkeypatch.setattr(activity, "info", lambda: MockActivityInfo())

        # テストデータ
        job_id = str(uuid.uuid4())
        tenant_id = "test-tenant"
        analysis_data = {
            AnalysisType.TYPE_A: {"value": 42, "source": "test"},
            AnalysisType.TYPE_B: {"value": 100, "source": "test"},
        }

        # アクティビティを実行
        result = await activities.process_analysis_data(
            job_id, tenant_id, analysis_data
        )

        # 結果の検証
        assert result is not None
        assert AnalysisType.TYPE_A.value in result
        assert AnalysisType.TYPE_B.value in result
        assert result[AnalysisType.TYPE_A.value]["processed"] is True
        assert result[AnalysisType.TYPE_B.value]["processed"] is True
        assert "timestamp" in result[AnalysisType.TYPE_A.value]
        assert "timestamp" in result[AnalysisType.TYPE_B.value]

    @pytest.mark.asyncio
    async def test_save_results(self, activities, monkeypatch):
        """save_resultsアクティビティのテスト"""

        # activityInfoをモック化
        class MockActivityInfo:
            def __init__(self):
                self.start_time = datetime.now(tz=UTC)

        monkeypatch.setattr(activity, "info", lambda: MockActivityInfo())

        # テストデータ
        job_id = str(uuid.uuid4())
        tenant_id = "test-tenant"
        results = {
            "type_a": {"value": 42, "processed": True},
            "type_b": {"value": 100, "processed": True},
        }

        # アクティビティを実行
        filepath = await activities.save_results(job_id, tenant_id, results)

        # 結果の検証
        assert filepath is not None
        path = Path(filepath)
        assert path.exists()

        # ファイルの内容を検証
        with path.open() as f:
            file_data = json.load(f)
            assert file_data["job_id"] == job_id
            assert file_data["tenant_id"] == tenant_id
            assert "results" in file_data
            assert "type_a" in file_data["results"]
            assert "type_b" in file_data["results"]
            assert file_data["results"]["type_a"]["processed"] is True
            assert file_data["results"]["type_b"]["processed"] is True

    @pytest.mark.asyncio
    async def test_save_results_error(self, activities, monkeypatch):
        """save_resultsアクティビティのエラーケースのテスト"""

        # activityInfoをモック化
        class MockActivityInfo:
            def __init__(self):
                self.start_time = datetime.now(tz=UTC)

        monkeypatch.setattr(activity, "info", lambda: MockActivityInfo())

        # 存在しない出力ディレクトリを設定
        activities.output_dir = "/non/existent/directory"

        # テストデータ
        job_id = str(uuid.uuid4())
        tenant_id = "test-tenant"
        results = {"test": "data"}

        # エラーが発生することを確認
        with pytest.raises(ApplicationError) as exc_info:
            await activities.save_results(job_id, tenant_id, results)

        # エラーメッセージを確認
        assert "Results saving failed" in str(exc_info.value)
