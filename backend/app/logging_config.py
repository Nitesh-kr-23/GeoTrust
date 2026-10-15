import logging
import sys

from app.config import settings


def configure_logging() -> None:
    level = logging.INFO if settings.is_production else logging.DEBUG
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
