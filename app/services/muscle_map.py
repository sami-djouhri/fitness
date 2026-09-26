"""Muscle group mapping, freshness colors, and Push/Pull/Legs classification."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Seed muscle names → SVG region mapping
# ---------------------------------------------------------------------------

MUSCLE_TO_REGION: dict[str, list[str]] = {
    "Brust": ["chest"],
    "Obere Brust": ["chest"],
    "Latissimus": ["back"],
    "Rückenstrecker": ["back"],
    "Unterer Rücken": ["back"],
    "Trapez": ["traps"],
    "Schultern": ["shoulders"],
    "Vordere Schulter": ["shoulders"],
    "Seitliche Schulter": ["shoulders"],
    "Hintere Schulter": ["shoulders"],
    "Bizeps": ["biceps"],
    "Unterarm": ["biceps"],
    "Trizeps": ["triceps"],
    "Quadrizeps": ["quads"],
    "Hüftbeuger": ["quads"],
    "Beinbizeps": ["hamstrings"],
    "Gesäß": ["hamstrings"],
    "Waden": ["calves"],
    "Bauch": ["core"],
    "Core": ["core"],
    "Seitliche Bauchmuskeln": ["core"],
    "Untere Bauchmuskeln": ["core"],
    # Composite entries
    "Beine": ["quads", "hamstrings", "calves"],
    "Ganzkörper": ["chest", "back", "traps", "shoulders", "biceps",
                   "triceps", "quads", "hamstrings", "calves", "core"],
    # No SVG region
    "Herz-Kreislauf": [],
}

ALL_REGIONS = [
    "chest", "back", "traps", "shoulders", "biceps",
    "triceps", "quads", "hamstrings", "calves", "core",
]

REGION_LABELS: dict[str, str] = {
    "chest": "Brust",
    "back": "Rücken",
    "traps": "Trapez",
    "shoulders": "Schultern",
    "biceps": "Bizeps",
    "triceps": "Trizeps",
    "quads": "Oberschenkel vorne",
    "hamstrings": "Oberschenkel hinten",
    "calves": "Waden",
    "core": "Core",
}

# Reverse: region → list of seed muscle names that map to it
REGION_TO_MUSCLES: dict[str, list[str]] = {}
for _muscle, _regions in MUSCLE_TO_REGION.items():
    for _r in _regions:
        REGION_TO_MUSCLES.setdefault(_r, [])
        if _muscle not in REGION_TO_MUSCLES[_r]:
            REGION_TO_MUSCLES[_r].append(_muscle)

# ---------------------------------------------------------------------------
# Push / Pull / Legs / Core classification
# ---------------------------------------------------------------------------

PPL_CATEGORIES: dict[str, list[str]] = {
    "push": ["chest", "shoulders", "triceps"],
    "pull": ["back", "traps", "biceps"],
    "legs": ["quads", "hamstrings", "calves"],
    "core": ["core"],
}

IDEAL_PPL_SPLIT: dict[str, float] = {
    "push": 0.30,
    "pull": 0.30,
    "legs": 0.30,
    "core": 0.10,
}

REGION_TO_PPL: dict[str, str] = {}
for _cat, _regions in PPL_CATEGORIES.items():
    for _r in _regions:
        REGION_TO_PPL[_r] = _cat

# ---------------------------------------------------------------------------
# Freshness color scale (days since last trained)
# ---------------------------------------------------------------------------

FRESHNESS_COLORS: list[tuple[int, str]] = [
    (2, "#22c55e"),    # 0–2 days: green (fresh)
    (4, "#4ade80"),    # 3–4 days: light green
    (6, "#facc15"),    # 5–6 days: yellow (due)
    (9, "#f97316"),    # 7–9 days: orange (overdue)
]
FRESHNESS_COLOR_STALE = "#ef4444"   # 10+ days: red (neglected)
FRESHNESS_COLOR_NEVER = "#475569"   # never trained: dark grey


def get_freshness_color(days: int | None) -> str:
    """Return hex color for the given number of days since last trained."""
    if days is None:
        return FRESHNESS_COLOR_NEVER
    for threshold, color in FRESHNESS_COLORS:
        if days <= threshold:
            return color
    return FRESHNESS_COLOR_STALE
