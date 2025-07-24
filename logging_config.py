import logging
import logging.config


def setup_logging():
    """Setup logging configuration using dictConfig"""

    config = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
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
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARN",
                "handlers": ["console"],
                "propagate": True,
            },
            "telethon_hook": {
                "level": "INFO",
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
