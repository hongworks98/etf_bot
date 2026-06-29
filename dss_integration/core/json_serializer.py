"""
dss_integration/core/json_serializer.py
DSSResult → JSON 직렬화.
dataclass, SimpleNamespace, Enum 등을 재귀적으로 변환한다.
"""
from __future__ import annotations
import dataclasses
import json
import math
from enum import Enum
from types import SimpleNamespace
from typing import Any


def _to_serializable(obj: Any, depth: int = 0) -> Any:
    """
    재귀적 직렬화. 최대 깊이 제한으로 무한 루프 방지.
    """
    if depth > 8:
        return str(obj)

    if obj is None or isinstance(obj, (bool, int, str)):
        return obj

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, Enum):
        return obj.value

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            k: _to_serializable(v, depth+1)
            for k, v in dataclasses.asdict(obj).items()
        }

    if isinstance(obj, SimpleNamespace):
        return {
            k: _to_serializable(v, depth+1)
            for k, v in vars(obj).items()
        }

    if isinstance(obj, dict):
        return {
            str(k): _to_serializable(v, depth+1)
            for k, v in obj.items()
        }

    if isinstance(obj, (list, tuple)):
        return [_to_serializable(item, depth+1) for item in obj]

    # 알 수 없는 객체 → 속성 dict 시도
    try:
        d = vars(obj)
        return {k: _to_serializable(v, depth+1) for k, v in d.items()
                if not k.startswith("_")}
    except TypeError:
        return str(obj)


class JSONSerializer:
    """DSSResult → JSON 변환 및 파일 저장."""

    def serialize(self, result: Any) -> dict:
        """DSSResult를 JSON 직렬화 가능한 dict로 변환."""
        return _to_serializable(result)

    def to_json(self, result: Any, indent: int = 2) -> str:
        """JSON 문자열 반환."""
        return json.dumps(self.serialize(result), ensure_ascii=False, indent=indent)

    def save(self, result: Any, path: str) -> None:
        """파일로 저장."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json(result))
