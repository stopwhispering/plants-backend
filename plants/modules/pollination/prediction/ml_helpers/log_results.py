from __future__ import annotations
import datetime
import json
from plants import local_config
from plants.modules.pollination.enums import PredictionModel


def log_results(model_category: PredictionModel,
                estimator: str,
                metrics: dict,
                training_stats: dict = None,
                notes: str = "",
                ) -> None:
    """Log the results of a machine learning retraining."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    log = {
        # utc timestamp in ISO 8601 format (e.g. '2026-01-10T18:18:33.328138+00:00')
        "timestamp": now_utc.isoformat(),
        "model": model_category,
        "estimator": estimator,
        "metrics": metrics,
        "training_stats": training_stats,
        "notes": notes,
    }
    log_file = (local_config.log_settings.training_logs_folder_path /
                f"{now_utc.strftime('%Y%m%d_%H%M%S')}_retrain_{model_category}.json")
    # dump the results to JSON
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
