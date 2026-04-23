from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from layers.probe import detect_file_kind
from shared.errors import (
    AmbiguousClassificationError,
    AppError,
    ClassificationUnderconfidentError,
    MissingRequiredParamError,
    NonInteractiveShellError,
)
from shared.probe import FileKind, HttpProbe, InputProbe
from shared.result import TaskResult
from shared.task import Classification, ExecutionRequest, TaskInput, TaskType

from .policies import HeuristicClassifier, analyze_shape
from .schema import DispatchConfig
from .services import Classifier, HttpObserver

TaskRunner = Callable[[ExecutionRequest], Awaitable[TaskResult]]

DEFAULT_MODEL_SPEC = "claude-opus-4-6"


async def plan(
    task_input: TaskInput,
    *,
    config: DispatchConfig | None = None,
    http_observer: HttpObserver | None = None,
    classifier: Classifier | None = None,
) -> ExecutionRequest:
    """TaskInput からの ExecutionRequest 構築

    Args:
        task_input: 入力
        config: dispatch 設定
        http_observer: HTTP 観測器
        classifier: 利用する Classifier

    Returns:
        実行可能な ExecutionRequest

    Raises:
        ClassificationUnderconfidentError: 信頼度が下限未満
        MissingRequiredParamError: 必須パラメータ欠落
        AmbiguousClassificationError: 対話不能下で曖昧
        NonInteractiveShellError: 対話不能下で確認必要
    """
    cfg = config or DispatchConfig()
    clf = classifier or HeuristicClassifier()

    explicit = task_input.explicit_type()
    if explicit is not None:
        return _request_from_explicit(task_input, explicit, reasoning="explicit --type")

    probe_result = await _observe(task_input.raw, http_observer=http_observer)
    classification = await clf.classify(probe_result)

    if classification.confidence < cfg.min_confidence:
        raise ClassificationUnderconfidentError(
            f"confidence {classification.confidence:.2f} < min {cfg.min_confidence:.2f}: "
            f"{classification.reasoning}"
        )

    if (
        classification.confidence < cfg.auto_run_confidence
        or classification.is_ambiguous(cfg.ambiguity_margin)
    ):
        classification = _resolve_ambiguity(classification, cfg, probe_result)

    missing = classification.missing_params(task_input.flags)
    if missing:
        raise MissingRequiredParamError(tuple(p.name for p in missing))

    params = {
        p.name: task_input.flags[p.name]
        for p in classification.required_params
        if p.name in task_input.flags
    }

    return ExecutionRequest(
        task_type=classification.task_type,
        input=task_input,
        params=params,
        model_spec=task_input.flags.get("model", DEFAULT_MODEL_SPEC),
        reasoning=classification.reasoning,
    )


async def _observe(raw: str, *, http_observer: HttpObserver | None) -> InputProbe:
    """入力観測の合成

    Args:
        raw: 入力文字列
        http_observer: HTTP 観測器

    Returns:
        shape と副作用観測を合成した InputProbe
    """
    shape = analyze_shape(raw)
    is_existing_path = False
    file_kind: FileKind | None = None

    try:
        p = Path(raw.strip())
        if p.exists() and p.is_file():
            is_existing_path = True
            file_kind = detect_file_kind(p)
    except OSError:
        pass

    http_info: HttpProbe | None = None
    if shape.is_http_url and http_observer is not None:
        http_info = await http_observer.observe(shape.raw)
    elif shape.is_http_url:
        from layers.probe import HttpxObserver

        http_info = await HttpxObserver().observe(shape.raw)

    return InputProbe(
        shape=shape,
        is_existing_path=is_existing_path,
        file_kind=file_kind,
        http=http_info,
    )


def _request_from_explicit(task_input: TaskInput, task_type: TaskType, *, reasoning: str) -> ExecutionRequest:
    """明示指定された task_type からの ExecutionRequest 組立

    Args:
        task_input: 入力
        task_type: 明示指定された TaskType
        reasoning: 理由文字列

    Returns:
        type フラグを除いた ExecutionRequest
    """
    flags = {k: v for k, v in task_input.flags.items() if k != "type"}
    return ExecutionRequest(
        task_type=task_type,
        input=task_input,
        params=flags,
        model_spec=task_input.flags.get("model", DEFAULT_MODEL_SPEC),
        reasoning=reasoning,
    )


def _resolve_ambiguity(
    classification: Classification,
    config: DispatchConfig,
    probe: InputProbe,
) -> Classification:
    """曖昧分類の対話確認もしくは失敗

    Args:
        classification: 曖昧な分類結果
        config: dispatch 設定
        probe: 入力観測結果

    Returns:
        ユーザ確認後の Classification

    Raises:
        NonInteractiveShellError: 対話不可の環境
    """
    if not config.interactive or not sys.stdin.isatty():
        raise NonInteractiveShellError(
            f"classification is ambiguous (conf={classification.confidence:.2f}) and TTY not available; "
            "supply --type explicitly"
        )
    return _prompt_user_for_classification(classification, probe)


def _prompt_user_for_classification(classification: Classification, probe: InputProbe) -> Classification:
    """対話プロンプトによる分類確認

    Args:
        classification: 提示対象の分類結果
        probe: 入力観測結果

    Returns:
        確認もしくは選択後の Classification

    Raises:
        AmbiguousClassificationError: ユーザ入力不能もしくは中断
    """
    print(f"[classifier] primary: {classification.task_type.value} (conf={classification.confidence:.2f})")
    print(f"[classifier] reason: {classification.reasoning}")
    for alt in classification.alternatives:
        print(f"[classifier] alt: {alt.task_type.value} (conf={alt.confidence:.2f})")
    try:
        answer = input("Accept primary [y], choose alt by index, or abort [q]? ").strip().lower()
    except EOFError as e:
        raise AmbiguousClassificationError("user input unavailable") from e
    if answer in ("", "y", "yes"):
        return classification
    if answer == "q":
        raise AmbiguousClassificationError("aborted by user")
    try:
        idx = int(answer)
        chosen = classification.alternatives[idx]
    except (ValueError, IndexError) as e:
        raise AmbiguousClassificationError(f"invalid choice: {answer}") from e
    return Classification(
        task_type=chosen.task_type,
        confidence=chosen.confidence,
        required_params=classification.required_params,
        alternatives=(),
        reasoning=f"manually chosen by user (was {classification.task_type.value})",
    )


async def run(
    task_input: TaskInput,
    *,
    runners: dict[TaskType, TaskRunner],
    classifier: Classifier | None = None,
    config: DispatchConfig | None = None,
) -> TaskResult:
    """plan と execute を連結した高レベルエントリ

    Args:
        task_input: 入力
        runners: TaskType 別 runner の写像
        classifier: 利用する Classifier
        config: dispatch 設定

    Returns:
        runner 由来の TaskResult
    """
    request = await plan(task_input, classifier=classifier, config=config)
    return await execute(request, runners=runners)


async def execute(request: ExecutionRequest, *, runners: dict[TaskType, TaskRunner]) -> TaskResult:
    """ExecutionRequest の task_type 別 runner 起動

    Args:
        request: 実行要求
        runners: TaskType 別 runner の写像

    Returns:
        runner 由来の TaskResult

    Raises:
        AppError: 写像に該当 TaskType が存在しない
    """
    runner = runners.get(request.task_type)
    if runner is None:
        raise AppError(f"unknown task type: {request.task_type}")
    return await runner(request)


def default_classifier() -> Classifier:
    """標準設定の Classifier 構築

    Returns:
        LLM 利用可能時の HybridClassifier もしくは HeuristicClassifier
    """
    try:
        from layers.llm_classifier import LlmClassifier

        from .policies import HybridClassifier

        return HybridClassifier(LlmClassifier())
    except Exception:
        return HeuristicClassifier()
