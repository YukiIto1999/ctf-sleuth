from __future__ import annotations

import ast
from pathlib import Path

import pytest

from foundation.skills import SKILLS, Skill, is_skill

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILLS_DIR = _REPO_ROOT / ".claude" / "skills"
_SRC_DIR = _REPO_ROOT / "src"


def _on_disk_names() -> set[str]:
    """`.claude/skills/` 配下のディレクトリ名集合

    Returns:
        ディレクトリ名の集合
    """
    return {p.name for p in _SKILLS_DIR.iterdir() if p.is_dir()}


def _collect_referenced() -> set[str]:
    """src/ 配下から参照される skill 名集合

    Returns:
        skill_names 引数 / _SKILLS / _KIND_SKILLS 経由の参照名集合
    """
    referenced: set[str] = set()

    class _Visitor(ast.NodeVisitor):
        """skill 名定義箇所の AST 訪問子"""

        def visit_keyword(self, node: ast.keyword) -> None:
            """skill_names 引数値の文字列要素抽出

            Args:
                node: keyword 引数 AST
            """
            if node.arg == "skill_names" and isinstance(node.value, ast.Tuple):
                for el in node.value.elts:
                    if isinstance(el, ast.Constant) and isinstance(el.value, str):
                        referenced.add(el.value)
            self.generic_visit(node)

        def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
            """_SKILLS と _KIND_SKILLS 代入の文字列要素抽出

            Args:
                node: 代入 AST
            """
            for tgt in node.targets:
                if not isinstance(tgt, ast.Name):
                    continue
                if tgt.id == "_SKILLS" and isinstance(node.value, ast.Tuple):
                    for el in node.value.elts:
                        if isinstance(el, ast.Constant) and isinstance(el.value, str):
                            referenced.add(el.value)
                elif tgt.id == "_KIND_SKILLS" and isinstance(node.value, ast.Dict):
                    for v in node.value.values:
                        if isinstance(v, ast.Tuple):
                            for el in v.elts:
                                if isinstance(el, ast.Constant) and isinstance(el.value, str):
                                    referenced.add(el.value)
            self.generic_visit(node)

    for path in _SRC_DIR.rglob("*.py"):
        _Visitor().visit(ast.parse(path.read_text()))
    return referenced


def test_registry_matches_disk() -> None:
    """SKILLS と `.claude/skills/` ディスク内容の一致検証"""
    on_disk = _on_disk_names()
    registered = {str(s) for s in SKILLS}
    missing = on_disk - registered
    extra = registered - on_disk
    assert not missing and not extra, f"missing={missing}, extra={extra}"


def test_referenced_skills_are_registered() -> None:
    """src/ 参照名の registry 登録検証"""
    for name in _collect_referenced():
        assert is_skill(name), f"unknown skill referenced: {name!r}"


def test_skill_constructor_accepts_known_name() -> None:
    """既知名に対する Skill コンストラクタの受理動作"""
    s = Skill("web-pentester")
    assert s == "web-pentester"
    assert isinstance(s, str)


def test_skill_constructor_rejects_unknown_name() -> None:
    """未登録名に対する Skill コンストラクタの ValueError 発生"""
    with pytest.raises(ValueError, match="unknown skill"):
        Skill("definitely-not-a-real-skill")


def test_is_skill_predicate() -> None:
    """is_skill の登録判定動作"""
    assert is_skill("web-pentester")
    assert not is_skill("definitely-not-a-real-skill")
