import logging
import logging.config
import os

logging_level = "DEBUG" if os.getenv("DEBUG", "").lower() in ("true", "1", "yes") else "INFO"


def setup_logging():
    """Setup logging configuration using dictConfig"""

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": logging_level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {  # root logger
                "level": "INFO",
                "handlers": ["console"],
            },
            "app": {
                "level": logging_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.pool": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.dialects": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.orm": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
            "telethon_hook": {
                "level": logging_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "fetch_messages": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sync_dialogs": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "dependency": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "user_repository": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "nebius": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)
