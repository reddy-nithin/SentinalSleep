"""AudioSet label utilities for the SentinelSleep detection layer.

The MIT AST model classifies audio into 527 AudioSet classes. This module
provides helpers that map the model's integer label IDs to human-readable
names and to distress weights defined in config.py.

Labels are loaded at runtime from the model's config rather than hardcoded
here, so they stay in sync with any future model update.
"""

from __future__ import annotations


def extract_label_map(model_config: object) -> dict[int, str]:
    """Return {label_id: label_name} from a loaded HuggingFace model config.

    Args:
        model_config: The `config` attribute of a loaded audio classification
            model (e.g., ``AutoModelForAudioClassification.from_pretrained(...).config``).

    Returns:
        Mapping from integer label index to AudioSet class name string.
    """
    return dict(model_config.id2label)  # type: ignore[attr-defined]


def build_distress_weight_map(
    id2label: dict[int, str],
    distress_classes: dict[str, float],
) -> dict[int, float]:
    """Map model label IDs to distress weights for matching distress classes.

    Any AudioSet label present in ``distress_classes`` gets its weight
    assigned to the corresponding integer ID. Labels not in
    ``distress_classes`` are omitted.

    Args:
        id2label: {label_id: label_name} from :func:`extract_label_map`.
        distress_classes: {label_name: weight} from
            ``config.DISTRESS_CLASS_WEIGHTS``.

    Returns:
        {label_id: weight} covering only labels found in ``distress_classes``.
    """
    return {
        idx: distress_classes[label]
        for idx, label in id2label.items()
        if label in distress_classes
    }


def find_unmatched_distress_labels(
    id2label: dict[int, str],
    distress_classes: dict[str, float],
) -> list[str]:
    """Return distress class names that have no corresponding model label.

    Useful for diagnosing mismatches between ``config.DISTRESS_CLASS_WEIGHTS``
    key strings and the exact AudioSet label strings used by the model.

    Args:
        id2label: {label_id: label_name} from :func:`extract_label_map`.
        distress_classes: {label_name: weight} from config.

    Returns:
        List of distress class names absent from the model's label vocabulary.
    """
    model_labels = set(id2label.values())
    return [name for name in distress_classes if name not in model_labels]
