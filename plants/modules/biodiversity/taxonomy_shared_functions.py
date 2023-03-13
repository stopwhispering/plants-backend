from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_accepted_synonym_label(powo_lookup: dict[str, Any]) -> str | None:
    """Parses synonyms from powo lookup dictionary into a string."""
    if powo_lookup.get("synonym"):
        if "accepted" in powo_lookup and "name" in powo_lookup["accepted"]:
            if isinstance(powo_lookup["accepted"], str):
                return "Accepted: " + powo_lookup["accepted"]
            if isinstance(powo_lookup["accepted"], dict):
                return (
                    "Accepted: "
                    + powo_lookup["accepted"]["name"]  # type: ignore[no-any-return]
                )
            logger.warning(
                f"Accepted synonym is neither a string nor a "
                f"dictionary: {powo_lookup['accepted']}"
            )
            return str(powo_lookup["accepted"])
        return "Accepted: unknown"
    return None


def get_concatenated_distribution(powo_lookup: dict[str, Any]) -> str | None:
    """Parses areas from powo lookup dictionary into a string."""
    if "distribution" in powo_lookup and "natives" in powo_lookup["distribution"]:
        result = (
            ", ".join([d["name"] for d in powo_lookup["distribution"]["natives"]])
            + " (natives)"
        )
    else:
        result = None

    if "distribution" in powo_lookup and "introduced" in powo_lookup["distribution"]:
        distribution_introduced = (
            ", ".join([d["name"] for d in powo_lookup["distribution"]["introduced"]])
            + " (introduced)"
        )

        result = (
            result + ", " + distribution_introduced
            if result
            else distribution_introduced
        )

    return result


def create_synonyms_concat(powo_lookup: dict[str, Any]) -> Optional[str]:
    """Parses synonyms from powo lookup dictionary into a string."""
    if "synonyms" in powo_lookup and powo_lookup["synonyms"]:
        return ", ".join([s["name"] for s in powo_lookup["synonyms"]])
    return None
