"""Distress Signal Score (DSS) calculator for the detection layer.

The DSS is a composite score in [0, 1] that summarises how strongly a
classifier output matches the acoustic signature of a PTSD nightmare.
It is computed as a weighted average of probabilities for distress-relevant
AudioSet classes, normalised by the maximum achievable weighted sum.

DSS > config.DSS_FLAG_THRESHOLD triggers escalation to the verification layer.
"""

from __future__ import annotations

from sentinelsleep import config


def compute_dss(
    probabilities: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Compute the Distress Signal Score from classifier output probabilities.

    The score is:

        DSS = sum(prob[c] * weight[c] for c in distress_classes) / max_possible

    where ``max_possible`` is the sum of all weights (the score achievable if
    every distress class fires at probability 1.0).

    Args:
        probabilities: ``{class_name: probability}`` from
            :meth:`ASTClassifier.classify`. Missing classes are treated as 0.
        weights: ``{class_name: weight}`` mapping. Defaults to
            ``config.DISTRESS_CLASS_WEIGHTS``.

    Returns:
        DSS in ``[0.0, 1.0]``. Returns 0.0 if ``weights`` is empty.
    """
    if weights is None:
        weights = config.DISTRESS_CLASS_WEIGHTS

    max_possible = sum(weights.values())
    if max_possible <= 0.0:
        return 0.0

    weighted_sum = sum(
        probabilities.get(label, 0.0) * weight
        for label, weight in weights.items()
    )
    return min(weighted_sum / max_possible, 1.0)


def is_flagged(
    dss: float,
    threshold: float = config.DSS_FLAG_THRESHOLD,
) -> bool:
    """Return True if DSS exceeds the flag threshold.

    Args:
        dss: Distress Signal Score from :func:`compute_dss`.
        threshold: Minimum DSS to escalate. Defaults to
            ``config.DSS_FLAG_THRESHOLD``.

    Returns:
        ``True`` if the score warrants escalation to the verification layer.
    """
    return dss > threshold


def top_distress_contributors(
    probabilities: dict[str, float],
    weights: dict[str, float] | None = None,
    top_k: int = 5,
) -> list[tuple[str, float, float]]:
    """Return the top-K distress classes contributing to the current DSS.

    Useful for logging and dashboard display to explain why a flag fired.

    Args:
        probabilities: ``{class_name: probability}`` from the classifier.
        weights: ``{class_name: weight}`` mapping. Defaults to
            ``config.DISTRESS_CLASS_WEIGHTS``.
        top_k: Number of top contributors to return.

    Returns:
        List of ``(class_name, probability, weighted_contribution)`` tuples,
        sorted descending by weighted contribution.
    """
    if weights is None:
        weights = config.DISTRESS_CLASS_WEIGHTS

    contributors = [
        (label, probabilities.get(label, 0.0), probabilities.get(label, 0.0) * w)
        for label, w in weights.items()
    ]
    contributors.sort(key=lambda t: t[2], reverse=True)
    return contributors[:top_k]
