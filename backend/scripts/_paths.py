"""Where the validation artefacts live.

The scripts run both from a checkout (`backend/scripts/…`, data one level above
`backend/`) and inside the API container (`/app/scripts/…`, data bind-mounted at
`/app/data`). Resolving the directory by walking up for a real `data/` keeps
both cases honest, and failing loudly beats silently measuring something else.
"""
from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("FSP_DATA_DIR")
    if override:
        return Path(override).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data"
        if candidate.is_dir():
            return candidate
    raise SystemExit(
        "Каталог data/ не найден. Запустите скрипт из репозитория или задайте FSP_DATA_DIR.\n"
        "В контейнере он монтируется в /app/data (см. docker-compose.yml)."
    )


DATA = data_dir()
SYNTHETIC = DATA / "synthetic"
LABELS = DATA / "labels"
VALIDATION = DATA / "validation"
