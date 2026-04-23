from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"

EXCLUDED_SRC_NAMES = {"__init__.py", "__main__.py"}


def src_target_for(test_path: Path) -> Path:
    """test ファイルの対応 src ファイルパスの算出

    Args:
        test_path: tests 配下の test_*.py 絶対パス

    Returns:
        src 配下の対応ファイル絶対パス
    """
    rel = test_path.relative_to(TESTS)
    parts = list(rel.parts)
    parts[-1] = parts[-1].removeprefix("test_")
    return SRC.joinpath(*parts)


def test_target_for(src_path: Path) -> Path:
    """src ファイルの対応 test ファイルパスの算出

    Args:
        src_path: src 配下の *.py 絶対パス

    Returns:
        tests 配下の対応ファイル絶対パス
    """
    rel = src_path.relative_to(SRC)
    parts = list(rel.parts)
    parts[-1] = "test_" + parts[-1]
    return TESTS.joinpath(*parts)


def all_test_files() -> list[Path]:
    """tests 配下の test_*.py 全列挙

    Returns:
        test_*.py のパスのリスト
    """
    return sorted(
        p for p in TESTS.rglob("test_*.py") if "__pycache__" not in p.parts
    )


def all_src_files() -> list[Path]:
    """src 配下の *.py 全列挙 (除外対象を除く)

    Returns:
        src 配下の *.py のパスのリスト
    """
    return sorted(
        p for p in SRC.rglob("*.py")
        if "__pycache__" not in p.parts and p.name not in EXCLUDED_SRC_NAMES
    )


def is_stub_body(body: list[ast.stmt]) -> bool:
    """関数 body が stub のみか判定

    Args:
        body: 関数 body

    Returns:
        body が docstring + `...` or `pass` or `raise NotImplementedError` のみなら True
    """
    stmts = [
        s for s in body
        if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
    ]
    if not stmts:
        return True
    if len(stmts) == 1:
        s = stmts[0]
        if isinstance(s, ast.Pass):
            return True
        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis:
            return True
        if isinstance(s, ast.Raise) and isinstance(s.exc, ast.Call):
            fn = s.exc.func
            if isinstance(fn, ast.Name) and fn.id == "NotImplementedError":
                return True
    return False


def classify_class(node: ast.ClassDef) -> str:
    """class 定義の分類

    Args:
        node: class 定義 AST

    Returns:
        "protocol" | "dataclass" | "enum" | "error_classvar_only" | "behavioral"
    """
    is_protocol = any(
        (isinstance(b, ast.Name) and b.id == "Protocol")
        or (isinstance(b, ast.Attribute) and b.attr == "Protocol")
        for b in node.bases
    )
    has_dataclass_decorator = any(
        (isinstance(d, ast.Name) and d.id == "dataclass")
        or (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass")
        for d in node.decorator_list
    )
    is_enum = any(
        (isinstance(b, ast.Name) and b.id in {"Enum", "StrEnum", "IntEnum"})
        or (isinstance(b, ast.Attribute) and b.attr in {"Enum", "StrEnum", "IntEnum"})
        for b in node.bases
    )
    is_error_base = any(
        isinstance(b, ast.Name) and (b.id.endswith("Error") or b.id == "Exception")
        for b in node.bases
    )

    method_bodies_non_stub = False
    has_method_defs = False
    non_field_non_docstring_statements = False

    for stmt in node.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            continue
        if isinstance(stmt, ast.AnnAssign):
            continue
        if isinstance(stmt, ast.Assign):
            continue
        if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
            has_method_defs = True
            if not is_stub_body(stmt.body):
                method_bodies_non_stub = True
            continue
        non_field_non_docstring_statements = True

    if is_protocol:
        if not method_bodies_non_stub and not non_field_non_docstring_statements:
            return "protocol"
    if is_enum:
        if not method_bodies_non_stub and not non_field_non_docstring_statements:
            return "enum"
    if has_dataclass_decorator:
        if not has_method_defs and not non_field_non_docstring_statements:
            return "dataclass"
    if is_error_base:
        if not method_bodies_non_stub and not non_field_non_docstring_statements:
            return "error_classvar_only"
    return "behavioral"


def classify_module(src_path: Path) -> str:
    """モジュール全体の分類

    Args:
        src_path: 判定対象 src ファイルの絶対パス

    Returns:
        "structural" (挙動なし、テスト不要) | "behavioral" (挙動あり、テスト必須) | "data_schema" (schema 定数のみ)
    """
    tree = ast.parse(src_path.read_text())

    top_level_behavioral = False
    class_only = True

    for stmt in tree.body:
        if isinstance(stmt, ast.Import | ast.ImportFrom):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            continue
        if isinstance(stmt, ast.Assign):
            target_is_all = (
                len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and stmt.targets[0].id == "__all__"
            )
            if target_is_all:
                continue
            if isinstance(stmt.value, ast.Constant | ast.Dict | ast.List | ast.Tuple | ast.Set):
                class_only = False
                continue
            if isinstance(stmt.value, ast.Call):
                class_only = False
                continue
            class_only = False
            continue
        if isinstance(stmt, ast.AnnAssign):
            class_only = False
            continue
        if isinstance(stmt, ast.ClassDef):
            kind = classify_class(stmt)
            if kind == "behavioral":
                top_level_behavioral = True
            continue
        if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
            if not is_stub_body(stmt.body):
                top_level_behavioral = True
            continue
        top_level_behavioral = True

    if top_level_behavioral:
        return "behavioral"
    if class_only:
        return "structural"
    return "data_schema"


def main() -> int:
    """test 配置の src 対称性検証

    Returns:
        違反あり 1 違反なし 0
    """
    errors: list[str] = []
    exempt: list[str] = []

    for test in all_test_files():
        src_target = src_target_for(test)
        if not src_target.exists():
            errors.append(
                f"test has no corresponding src: {test.relative_to(ROOT)} -> expected {src_target.relative_to(ROOT)}"
            )

    for src in all_src_files():
        expected_test = test_target_for(src)
        if expected_test.exists():
            continue
        kind = classify_module(src)
        if kind in {"structural", "data_schema"}:
            exempt.append(f"  [exempt:{kind}] {src.relative_to(ROOT)}")
            continue
        errors.append(
            f"behavioral src has no corresponding test: {src.relative_to(ROOT)} -> expected {expected_test.relative_to(ROOT)}"
        )

    tests_count = len(all_test_files())
    src_count = len(all_src_files())
    exempt_count = len(exempt)

    if errors:
        print("test layout violations:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        if exempt:
            print("\nexempt (structural / data_schema, no test required):", file=sys.stderr)
            for e in exempt:
                print(e, file=sys.stderr)
        print(f"\n{len(errors)} violation(s), {exempt_count} exempt", file=sys.stderr)
        return 1

    print(f"test layout ok ({tests_count} tests / {src_count} src files, {exempt_count} structural exempt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
