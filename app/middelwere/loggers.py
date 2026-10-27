import uuid
import logging.config
import time
import structlog

from ..core.config import settings


class LoggingMiddleware:
    def __init__(self, app) -> None:
        self.app = app
        self.logger_struc = structlog.get_logger("access")
        self.logger_ing = logging.getLogger(__name__)

        self.configure_logging()
        self.logger_ing.info("LoggingMiddleware initialized")

    def configure_logging(self) -> None:
        level = settings.logging.level

        timestamp = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")
        shared_processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            timestamp,
        ]

        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "plain": {
                        "()": structlog.stdlib.ProcessorFormatter,
                        "processors": [
                            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                            structlog.dev.ConsoleRenderer(colors=False),
                        ],
                        "foreign_pre_chain": shared_processors,
                    },
                    "colored": {
                        "()": structlog.stdlib.ProcessorFormatter,
                        "processors": [
                            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                            structlog.dev.ConsoleRenderer(colors=True),
                        ],
                        "foreign_pre_chain": shared_processors,
                    },
                },
                "handlers": {
                    "default": {
                        "level": level,
                        "class": "logging.StreamHandler",
                        "formatter": "colored",
                    },
                },
                "loggers": {
                    "": {
                        "handlers": ["default"],
                        "level": level,
                        "propagate": True,
                    },
                },
            }
        )

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                timestamp,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        status_code = None

        async def send_wrapper(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", request_id.encode()))
            await send(message)

        start_time = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration = time.perf_counter() - start_time
            self.logger_struc.exception(
                "request_failed",
                method=scope.get("method"),
                path=scope.get("path"),
                duration=round(duration, 4),
            )
            raise
        else:
            duration = time.perf_counter() - start_time
            self.logger_struc.info(
                "request_completed",
                method=scope.get("method"),
                path=scope.get("path"),
                request_id=request_id,
                status_code=status_code,
                duration=round(duration, 4),
            )
