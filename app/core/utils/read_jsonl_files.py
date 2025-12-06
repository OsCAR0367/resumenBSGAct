import json
import os
import datetime
from typing import Any, List
from app.core.setup_config import settings


def read_jsonl_files(filter_key: str, filter_value: Any) -> List[dict]:
    resultados = []

    for filename in os.listdir(settings.LOG_DIR):

        # Acepta archivos que comienzan con .jsonl (incluye .jsonl, .jsonl.1, .jsonl.2...)
        if filename.endswith(".jsonl") or ".jsonl." in filename:
            full_path = os.path.join(settings.LOG_DIR, filename)

            with open(full_path, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)

                        # Filtrar por key/value
                        if data.get(filter_key) == filter_value:
                            resultados.append(data)

                    except json.JSONDecodeError:
                        continue

    # Ordenar por timestamp si existe
    resultados.sort(
        key=lambda x: datetime.fromisoformat(
            x["timestamp"].replace("Z", "+00:00")
        ) if "timestamp" in x else datetime.min
    )

    return resultados

