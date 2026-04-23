from __future__ import annotations

from dataclasses import dataclass

from shared.task import Strategy


@dataclass(frozen=True, slots=True)
class ChallengeId:
    """CTFd 内の challenge 整数識別子

    Attributes:
        value: CTFd 側の ID 整数
    """

    value: int


@dataclass(frozen=True, slots=True)
class Hint:
    """challenge に付与された hint

    Attributes:
        content: hint 本文
        cost: 公開に必要なポイント
    """

    content: str
    cost: int = 0


@dataclass(frozen=True, slots=True)
class Challenge:
    """CTFd 上の 1 challenge の不変表現

    Attributes:
        id: CTFd 内部 ID
        name: 表示名
        category_raw: CTFd 由来の category 文字列
        strategy: 正規化された Strategy
        description: Markdown 変換済の説明文
        value: 観測時点の配点
        connection_info: サービス接続情報
        tags: CTFd 側のタグ一覧
        hints: Hint のタプル
        distfile_urls: 配布ファイル URL のタプル
    """

    id: ChallengeId
    name: str
    category_raw: str
    strategy: Strategy | None
    description: str = ""
    value: int = 0
    connection_info: str = ""
    tags: tuple[str, ...] = ()
    hints: tuple[Hint, ...] = ()
    distfile_urls: tuple[str, ...] = ()

    def slug(self) -> str:
        """slug 文字列の生成

        Returns:
            ファイルシステム安全な短縮名
        """
        from ..policies.slug import slugify

        return slugify(self.name) or f"challenge-{self.id.value}"
