from __future__ import annotations

from contexts.ctf_challenge.domain import Challenge, ChallengeId, Hint
from contexts.ctf_challenge.solve.prompts import build_system_prompt
from shared.task import Strategy


def _ch(
    name: str = "test",
    category: str = "Pwn",
    strategy: Strategy | None = Strategy.PWN,
    **overrides: object,
) -> Challenge:
    """テスト用 Challenge の生成

    Args:
        name: challenge 名
        category: category 文字列
        strategy: Strategy もしくは None
        **overrides: 個別フィールドの上書き

    Returns:
        組立済 Challenge
    """
    kwargs = {
        "id": ChallengeId(1),
        "name": name,
        "category_raw": category,
        "strategy": strategy,
        "description": "desc",
        "value": 100,
        "connection_info": "",
        "tags": (),
        "hints": (),
        "distfile_urls": (),
    }
    kwargs.update(overrides)
    return Challenge(**kwargs)  # type: ignore[arg-type]


def test_role_section_always_present() -> None:
    """Role セクションの常時出現"""
    out = build_system_prompt(challenge=_ch())
    assert "# Role" in out
    assert "expert CTF solver" in out


def test_challenge_metadata_is_included() -> None:
    """challenge メタ情報の出現"""
    out = build_system_prompt(challenge=_ch(name="my-pwn", category="Pwn"))
    assert "my-pwn" in out
    assert "**Category** : Pwn (strategy: pwn)" in out


def test_unknown_strategy_label_omitted() -> None:
    """未知 strategy 時のラベル省略"""
    out = build_system_prompt(challenge=_ch(category="Quiz", strategy=None))
    assert "**Category** : Quiz" in out
    assert "strategy:" not in out


def test_tags_shown_when_present() -> None:
    """tags 存在時の列挙"""
    out = build_system_prompt(challenge=_ch(tags=("warmup", "easy")))
    assert "**Tags**     : warmup, easy" in out


def test_tags_omitted_when_empty() -> None:
    """空 tags の省略"""
    out = build_system_prompt(challenge=_ch(tags=()))
    assert "**Tags**" not in out


def test_description_placeholder_when_empty() -> None:
    """description 空時のプレースホルダ"""
    out = build_system_prompt(challenge=_ch(description=""))
    assert "_No description provided._" in out


def test_service_connection_renders_for_url() -> None:
    """URL 接続情報の Web サービス hint"""
    out = build_system_prompt(
        challenge=_ch(connection_info="https://target.example.com/"),
    )
    assert "## Service Connection" in out
    assert "https://target.example.com/" in out
    assert "Web service" in out


def test_service_connection_renders_for_nc() -> None:
    """nc 接続情報の TCP サービス hint"""
    out = build_system_prompt(challenge=_ch(connection_info="nc target.com 1337"))
    assert "TCP service" in out
    assert "heredoc" in out


def test_service_connection_absent_when_no_info() -> None:
    """接続情報不在時のセクション省略"""
    out = build_system_prompt(challenge=_ch(connection_info=""))
    assert "## Service Connection" not in out


def test_localhost_rewritten_to_host_docker_internal() -> None:
    """localhost の host.docker.internal 書換"""
    out = build_system_prompt(
        challenge=_ch(connection_info="nc localhost 9999"),
    )
    assert "host.docker.internal" in out
    assert "localhost" not in out


def test_distfiles_listed_under_challenge_distfiles_path() -> None:
    """distfile のパス列挙"""
    out = build_system_prompt(
        challenge=_ch(),
        distfile_names=("binary", "hint.txt"),
    )
    assert "/challenge/distfiles/binary" in out
    assert "/challenge/distfiles/hint.txt" in out


def test_hints_section_shows_visible_hints_only() -> None:
    """空 content Hint の除外"""
    out = build_system_prompt(
        challenge=_ch(hints=(Hint(content="try strings", cost=0), Hint(content="", cost=5))),
    )
    assert "try strings" in out
    assert "cost=5" not in out
    assert out.count("\n- ") >= 1


def test_strategy_section_renders_for_known_category() -> None:
    """既知 strategy での section 描画"""
    out = build_system_prompt(challenge=_ch(strategy=Strategy.PWN))
    assert "## Pwn strategy" in out
    assert "pwntools" in out


def test_skills_section_lists_suggested_names() -> None:
    """関連 skill 名の列挙"""
    out = build_system_prompt(challenge=_ch(strategy=Strategy.WEB))
    assert "## Related Skills" in out
    assert "`injection`" in out


def test_rules_section_always_present() -> None:
    """Rules セクションの常時出現"""
    out = build_system_prompt(challenge=_ch())
    assert "# Rules" in out
    assert "submit_flag" in out


def test_output_is_deterministic() -> None:
    """同一入力での同一出力"""
    c = _ch(name="x", strategy=Strategy.WEB, tags=("a", "b"))
    a = build_system_prompt(challenge=c, distfile_names=("bin",), container_arch="x86_64")
    b = build_system_prompt(challenge=c, distfile_names=("bin",), container_arch="x86_64")
    assert a == b


def test_output_ends_with_single_newline() -> None:
    """末尾改行の単一化"""
    out = build_system_prompt(challenge=_ch())
    assert out.endswith("\n")
    assert not out.endswith("\n\n")
