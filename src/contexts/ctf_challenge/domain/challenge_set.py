from __future__ import annotations

from dataclasses import dataclass

from .challenge import Challenge


@dataclass(frozen=True, slots=True)
class ChallengeSet:
    """CTFd 由来の challenge 集合と solved 状態

    Attributes:
        challenges: Challenge のタプル
        solved_names: solved 判定済 challenge 名の集合
    """

    challenges: tuple[Challenge, ...]
    solved_names: frozenset[str] = frozenset()

    def unsolved(self) -> tuple[Challenge, ...]:
        """未 solve challenge の抽出

        Returns:
            solved_names に含まれない Challenge のタプル
        """
        return tuple(c for c in self.challenges if c.name not in self.solved_names)

    def by_name(self, name: str) -> Challenge | None:
        """名前指定での Challenge 参照

        Args:
            name: Challenge 名

        Returns:
            一致する Challenge もしくは None
        """
        for c in self.challenges:
            if c.name == name:
                return c
        return None
