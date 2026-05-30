"""Agent Package JSON Schema validator."""

import json
from typing import Tuple, List

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


AGENT_PACKAGE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "AgentPackage",
    "description": "标准化智能体描述包 v1.0.0",
    "type": "object",
    "required": ["metadata", "identity"],
    "additionalProperties": False,
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["name", "version", "schema_version", "source_platform", "export_timestamp", "tool_version"],
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 128},
                "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"},
                "schema_version": {"type": "string", "const": "1.0.0"},
                "source_platform": {"type": "string", "minLength": 1, "maxLength": 64},
                "export_timestamp": {"type": "string"},
                "tool_version": {"type": "string"},
                "description": {"type": "string", "maxLength": 2048},
                "author": {"type": "string", "maxLength": 128},
                "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 32},
            },
        },
        "identity": {
            "type": "object",
            "required": ["system_prompt"],
            "properties": {
                "system_prompt": {"type": "string", "maxLength": 100000},
                "role_description": {"type": "string", "maxLength": 10000},
                "personality_traits": {"type": "array", "items": {"type": "string"}},
                "source_files": {"type": "array", "items": {"type": "string"}},
            },
        },
        "tools": {"type": "array", "maxItems": 128, "items": {"type": "object"}},
        "workflows": {"type": "array", "maxItems": 64, "items": {"type": "object"}},
        "skills": {"type": "array", "maxItems": 128, "items": {"type": "object"}},
        "steering": {"type": "array", "maxItems": 64, "items": {"type": "object"}},
        "memory": {"type": "object"},
        "hooks": {"type": "array", "maxItems": 64, "items": {"type": "object"}},
        "dependencies": {"type": "array", "maxItems": 256, "items": {"type": "object"}},
        "distillation_report": {"type": "object"},
        "signature": {"type": "object"},
    },
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


class ValidationError:
    """校验错误"""
    def __init__(self, path: str, category: str, message: str):
        self.path = path
        self.category = category  # missing_required|invalid_type|invalid_format|unknown_field|constraint_violation
        self.message = message

    def to_dict(self) -> dict:
        return {"path": self.path, "category": self.category, "message": self.message}

    def __repr__(self):
        return f"ValidationError({self.path}: {self.category} - {self.message})"


class SchemaValidator:
    """Agent Package Schema 校验器"""

    def validate(self, data: dict) -> Tuple[bool, List[ValidationError]]:
        """校验 Agent Package 数据结构。返回 (is_valid, errors)"""
        if HAS_JSONSCHEMA:
            return self._validate_with_jsonschema(data)
        else:
            return self._validate_basic(data)

    def validate_file(self, file_path: str) -> Tuple[bool, List[ValidationError]]:
        """校验 .agentpkg.json 文件"""
        import os

        # 文件大小检查
        try:
            size = os.path.getsize(file_path)
        except OSError as e:
            return False, [ValidationError("/", "invalid_format", f"Cannot read file: {e}")]

        if size > MAX_FILE_SIZE:
            return False, [ValidationError("/", "constraint_violation",
                          f"File size {size} bytes exceeds limit of {MAX_FILE_SIZE} bytes")]

        # JSON 解析
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return False, [ValidationError("/", "invalid_format",
                          f"JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}")]
        except Exception as e:
            return False, [ValidationError("/", "invalid_format", f"Read error: {e}")]

        return self.validate(data)

    def _validate_with_jsonschema(self, data: dict) -> Tuple[bool, List[ValidationError]]:
        """使用 jsonschema 库校验"""
        validator = jsonschema.Draft202012Validator(AGENT_PACKAGE_SCHEMA)
        errors = []
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            path = "/" + "/".join(str(p) for p in error.absolute_path) if error.absolute_path else "/"
            category = self._classify_error(error)
            errors.append(ValidationError(path, category, error.message))
        return len(errors) == 0, errors

    def _validate_basic(self, data: dict) -> Tuple[bool, List[ValidationError]]:
        """基础校验（无 jsonschema 时的回退）"""
        errors = []

        if not isinstance(data, dict):
            errors.append(ValidationError("/", "invalid_type", "Root must be an object"))
            return False, errors

        # 必填字段
        for field in ["metadata", "identity"]:
            if field not in data:
                errors.append(ValidationError(f"/{field}", "missing_required", f"Missing required field: {field}"))

        if "metadata" in data and isinstance(data["metadata"], dict):
            meta = data["metadata"]
            for field in ["name", "version", "schema_version", "source_platform", "export_timestamp", "tool_version"]:
                if field not in meta:
                    errors.append(ValidationError(f"/metadata/{field}", "missing_required",
                                 f"Missing required field: metadata.{field}"))

        if "identity" in data and isinstance(data["identity"], dict):
            if "system_prompt" not in data["identity"]:
                errors.append(ValidationError("/identity/system_prompt", "missing_required",
                             "Missing required field: identity.system_prompt"))

        # 未知顶层字段
        allowed = set(AGENT_PACKAGE_SCHEMA["properties"].keys())
        for key in data:
            if key not in allowed:
                errors.append(ValidationError(f"/{key}", "unknown_field", f"Unknown field: {key}"))

        return len(errors) == 0, errors

    def _classify_error(self, error) -> str:
        """将 jsonschema 错误分类"""
        validator = error.validator
        if validator == "required":
            return "missing_required"
        elif validator == "type":
            return "invalid_type"
        elif validator in ("pattern", "format", "const"):
            return "invalid_format"
        elif validator == "additionalProperties":
            return "unknown_field"
        else:
            return "constraint_violation"
