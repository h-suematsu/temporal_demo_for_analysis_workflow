from dataclasses import dataclass
from enum import Enum
from typing import Any


class AnalysisType(str, Enum):
    TYPE_A = "type_a"
    TYPE_B = "type_b"
    TYPE_C = "type_c"


@dataclass
class AnalysisRequest:
    job_id: str
    tenant_id: str
    analysis_type: str


@dataclass
class AnalysisResult:
    job_id: str
    tenant_id: str
    analysis_type: str
    data: dict[str, Any]


@dataclass
class ProxyWorkflowInput:
    """Proxy Workflowへの入力モデル"""

    # PubSubメッセージのペイロード
    payload: dict[str, Any]


@dataclass
class AnalysisWorkflowInput:
    """Analysis Workflowへの入力モデル"""

    job_id: str
    tenant_id: str
