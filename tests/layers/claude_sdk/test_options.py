from __future__ import annotations

from layers.claude_sdk.options import build_options


def _opts(**overrides: object):
    """テスト用 build_options 呼出ヘルパ

    Args:
        **overrides: 個別フィールドの上書き

    Returns:
        ClaudeAgentOptions
    """
    kwargs = {
        "model_spec": "claude-opus-4-6",
        "system_prompt": "sp",
        "allowed_tools": ["Bash"],
    }
    kwargs.update(overrides)
    return build_options(**kwargs)  # type: ignore[arg-type]


def test_default_enables_all_skills() -> None:
    """デフォルトの skills=all 強制"""
    assert _opts().skills == "all"


def test_default_setting_sources_is_project() -> None:
    """デフォルトの setting_sources=project 強制"""
    assert _opts().setting_sources == ["project"]


def test_explicit_skills_none_removes_setting_sources() -> None:
    """skills=None 明示時の setting_sources 同時解除"""
    opts = _opts(skills=None)
    assert opts.skills is None
    assert opts.setting_sources is None


def test_skills_list_is_passed_through() -> None:
    """skills リスト指定の素通し"""
    opts = _opts(skills=["dfir", "reconnaissance"])
    assert opts.skills == ["dfir", "reconnaissance"]
    assert opts.setting_sources == ["project"]


def test_allowed_tools_preserved() -> None:
    """allowed_tools の保持"""
    opts = _opts(allowed_tools=["Bash", "WebFetch", "WebSearch"])
    assert opts.allowed_tools == ["Bash", "WebFetch", "WebSearch"]


def test_allowed_tools_defaults_to_empty() -> None:
    """allowed_tools 未指定時の空リスト化"""
    opts = _opts(allowed_tools=None)
    assert opts.allowed_tools == []


def test_model_is_applied() -> None:
    """model_spec の反映"""
    opts = _opts(model_spec="claude-haiku-4-5")
    assert opts.model == "claude-haiku-4-5"


def test_permission_mode_bypass() -> None:
    """permission_mode=bypass の強制"""
    assert _opts().permission_mode == "bypassPermissions"


def test_claudecode_env_cleared() -> None:
    """CLAUDECODE 環境変数の空化"""
    assert _opts().env.get("CLAUDECODE") == ""


def test_output_format_is_forwarded() -> None:
    """output_format の素通し"""
    schema = {"type": "json_schema", "schema": {"type": "object"}}
    opts = _opts(output_format=schema)
    assert opts.output_format == schema


def test_effort_is_forwarded() -> None:
    """effort の素通し"""
    opts = _opts(effort="high")
    assert opts.effort == "high"
