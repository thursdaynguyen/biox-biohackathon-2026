from __future__ import annotations

from backend.schemas import SolutionPoint


def build_optimum_point(
    parameters: dict[str, float],
    score: float | None,
) -> SolutionPoint:
    return SolutionPoint(
        parameters=parameters,
        score=score,
        metadata={"source": "backend-placeholder"},
    )


def build_topk_candidates(
    parameters: dict[str, float],
    base_score: float | None,
    top_k: int,
) -> list[SolutionPoint]:
    candidates: list[SolutionPoint] = [
        build_optimum_point(parameters=parameters, score=base_score)
    ]

    while len(candidates) < top_k:
        candidates.append(
            SolutionPoint(
                parameters=dict(parameters),
                score=base_score,
                metadata={"source": "backend-placeholder", "duplicate": True},
            )
        )

    return candidates[:top_k]
