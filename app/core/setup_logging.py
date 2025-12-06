import atexit
import logging.config

from app.core.setup_config import settings

def setup_logging():
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "[%(levelname)s|%(module)s|L%(lineno)d] %(asctime)s: %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z"
            },
            "json": {
                "()": "app.core.app_json_formatter.AppJSONFormatter",
                "fmt_keys": {
                    "level": "levelname",
                    "message": "message",
                    "timestamp": "timestamp",
                    "logger": "name",
                    "module": "module",
                    "function": "funcName",
                    "line": "lineno",
                    "thread_name": "threadName"
                }
            }
        },
        "handlers": {
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "simple",
                "stream": "ext://sys.stderr"
            },
            "file_json": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": f"{settings.LOG_DIR}/{settings.PROJECT_NAME.lower().replace(" ", "_")}.log.jsonl",
                "maxBytes": 10000,
                "backupCount": 30
            },
            "queue_handler": {
                "class": "app.core.app_json_formatter.AppQueueHandler",
                "handlers": [
                    "stderr",
                    "file_json"
                ],
                "respect_handler_level": True
            }
        },
        "loggers": {
            "root": {
                "level": "DEBUG",
                "handlers": [
                    "queue_handler"
                ]
            }
        }
    }
    logging.config.dictConfig(config)

    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)


def get_logger_app():
    logger = logging.getLogger(settings.PROJECT_NAME.lower().replace(" ", "_"))
    return logger

logger = get_logger_app()
