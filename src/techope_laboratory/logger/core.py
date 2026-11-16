"""Provide a custom logger setup."""

import atexit
import datetime
import encodings.utf_8
import json
import logging
import logging.handlers
import pathlib
import platform
import queue
import re
import sys
import threading
import unicodedata
from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar, Final, TextIO

import platformdirs

__lock: Final[threading.Lock] = threading.Lock()
__author_name: Final[str] = "techope"
__application_name: Final[str] = "laboratory"
__log_queue: Final[queue.Queue[logging.LogRecord]] = queue.Queue(
    maxsize=100,
)
__queue_listener: (
    Final[logging.handlers.QueueListener]
) = logging.handlers.QueueListener(
    queue=__log_queue,
    respect_handler_level=True,
)


def __get_default_logs_folder_path(
    p_application_name: str,
    p_author_name: str | None = None,
) -> pathlib.Path:
    """
    Retrieve the default log folder path.

    Use the operating system and application name to determine the folder path.
    It creates the necessary directories if they do not exist.

    :param p_application_name: The name of the application for which logs are
     being retrieved.
    :param p_author_name: The author or organization name associated with the
     application.
    :return: A path to the default log folder.
    """
    # 1. Retrieve the ideal log folder based on the OS.
    # Windows:
    #   C:/Users/<User>/AppData/Local/<author_name>/<application_name>/Logs
    # MacOS:
    #   ~/Library/Logs/<application_name>
    # Linux:
    #   ~/.local/state/<application_name>/log
    l_logs_folder: pathlib.Path = platformdirs.user_log_path(
        appname=p_application_name,
        appauthor=p_author_name,
    )

    # 2. Create the folder and its parents if they do not exist yet.
    l_logs_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 3. Return the path of the log folder.
    return l_logs_folder


class __CustomFormatter(
    logging.Formatter,
):
    """Base class for custom log formatters."""

    EMPTY_RECORD: ClassVar[Final[logging.LogRecord]] = logging.LogRecord(
        name="logger_name",
        level=0,
        pathname="example/example.txt",
        lineno=1,
        msg="message for nothing",
        args=None,
        exc_info=None,
    )

    def __init__(
        self,
    ) -> None:
        super().__init__(
            fmt=None,
            datefmt=None,
            style="%",
            validate=True,
            defaults=None,
        )

    def _format(
        self,
        p_record: logging.LogRecord,
        **p_base_data: dict[str, str | int],
    ) -> str:
        """
        Create the payload from the record.

        :param p_base_data: Data to include in the payload.
        :param p_record: The record to use to create the payload.
        :return: The payload serialized as a JSON string.
        """
        l_data = {
            "timestamp": datetime.datetime.fromtimestamp(
                timestamp=p_record.created,
                tz=datetime.UTC,
            ).astimezone().isoformat(),
            "level": p_record.levelname,
            "logger": p_record.name,
        }

        l_data.update(
            p_base_data,
            line=p_record.lineno,
            message=p_record.getMessage(),
        )

        if p_record.exc_info:
            l_data["exception"] = self.formatException(
                ei=p_record.exc_info,
            )

        for l_key, l_value in p_record.__dict__.items():
            if l_key not in self.EMPTY_RECORD.__dict__:
                l_data[l_key] = l_value

        return json.dumps(
            obj=l_data,
            ensure_ascii=False,
            default=str,
        )


class __CustomConsoleFormatter(
    __CustomFormatter,
):
    """Custom console formatter with dynamic ANSI color handling."""

    COLORS_BY_LOG_LEVEL: ClassVar[Final[Mapping[int, str]]] = MappingProxyType({
        # Cyan.
        logging.DEBUG: "\033[36m",

        # Green.
        logging.INFO: "\033[32m",

        # Yellow.
        logging.WARNING: "\033[33m",

        # Red.
        logging.ERROR: "\033[31m",

        # Background red.
        logging.CRITICAL: "\033[41m",
    })

    COLOR_RESET: ClassVar[Final[str]] = "\033[0m"

    def format(
        self,
        p_record: logging.LogRecord,
    ) -> str:
        """
        Format the log record using ANSI colors and JSON format.

        :param p_record: The log record to format.
        :return: The formatted log message as a string.
        """
        l_payload: str = self._format(
            p_record=p_record,
            module=p_record.module,
        )

        return (
            "".join((
                self.COLORS_BY_LOG_LEVEL[p_record.levelno],
                l_payload,
                self.COLOR_RESET,
            )) if p_record.levelno in self.COLORS_BY_LOG_LEVEL else
            l_payload
        )


class __CustomFileFormatter(
    __CustomFormatter,
):
    """Custom file formatter."""

    def format(
        self,
        p_record: logging.LogRecord,
    ) -> str:
        """
        Format the log record in a JSON format.

        :param record: The log record to format.
        :return: The formatted log message as a string.
        """
        return self._format(
            p_record=p_record,
            file_path=p_record.pathname,
            function=p_record.funcName,
        )


__techope_laboratory_logger_name: Final[str] = "_".join((
    __author_name,
    __application_name,
))


def __configure_root_logger(
    p_display_log_folder_path: bool = False,
    p_send_logs_to_server: bool = True,
) -> None:
    """
    Configure a root logger for the techope_laboratory project.

    :param p_display_log_folder_path: Indicates if the path to the log folder
     must be displayed in the console.
    :param p_send_logs_to_server: Send logs to a server. (Syslog for Linux / Not
     implemented for Windows / Not implemented for Java).
    """
    l_techope_laboratory_logger: logging.Logger = logging.getLogger(
        name=__techope_laboratory_logger_name,
    )

    # Avoid log duplication if the logger is retrieved multiple times.
    with __lock:
        if not l_techope_laboratory_logger.handlers:
            l_techope_laboratory_logger.setLevel(
                level=logging.DEBUG,
            )

            # Creation of the rotating file handler.
            l_techope_laboratory_log_file_path: (
                pathlib.Path
            ) = __get_default_logs_folder_path(
                p_application_name=__application_name,
                p_author_name=__author_name,
            ).joinpath(
                f"{l_techope_laboratory_logger.name}.log",
            )

            # Makes sure the directory exists.
            l_techope_laboratory_log_file_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            l_techope_laboratory_file_handler: (
                logging.handlers.RotatingFileHandler
            ) = logging.handlers.RotatingFileHandler(
                filename=l_techope_laboratory_log_file_path,
                # 5Mo.
                maxBytes=5 * 1024 * 1024,
                backupCount=10,
                encoding=encodings.utf_8.getregentry().name,
            )
            l_techope_laboratory_file_handler.setLevel(
                level=logging.DEBUG,
            )
            l_techope_laboratory_file_handler.setFormatter(
                fmt=__CustomFileFormatter(),
            )
            l_techope_laboratory_file_handler.addFilter(
                filter=lambda l_record: l_record.name.startswith(
                    l_techope_laboratory_logger.name,
                ),
            )

            # Creation of the console handler.
            l_techope_laboratory_console_handler: (
                logging.StreamHandler[TextIO]
            ) = logging.StreamHandler(
                stream=sys.stdout,
            )
            l_techope_laboratory_console_handler.setLevel(
                level=logging.DEBUG,
            )
            l_techope_laboratory_console_handler.setFormatter(
                fmt=__CustomConsoleFormatter(),
            )

            # Add a filter so only the logs from the root logger are displayed
            # in the console.
            l_techope_laboratory_console_handler.addFilter(
                filter=lambda l_record: (
                    l_record.name == l_techope_laboratory_logger.name and
                    not getattr(
                        l_record,
                        "_to_ignore_for_stream_handler",
                        False,
                    )
                ),
            )

            __queue_listener.handlers += (
                l_techope_laboratory_file_handler,
                l_techope_laboratory_console_handler,
            )

            __queue_listener.start()

            l_techope_laboratory_logger.addHandler(
                hdlr=logging.handlers.QueueHandler(
                    queue=__log_queue,
                ),
            )

            if p_send_logs_to_server:
                match (l_platform := platform.system()):
                    case "Linux":
                        try:
                            l_techope_laboratory_server_handler: (
                                logging.handlers.SysLogHandler
                            ) = logging.handlers.SysLogHandler(
                                address="/dev/log",
                            )
                        except Exception:
                            l_techope_laboratory_logger.warning(
                                msg="Failed to connectec to Syslog server.",
                                exc_info=True,
                            )
                        else:
                            l_techope_laboratory_server_handler.setLevel(
                                level=logging.DEBUG,
                            )
                            l_techope_laboratory_server_handler.setFormatter(
                                fmt=__CustomFileFormatter(),
                            )
                            l_techope_laboratory_server_handler.addFilter(
                                filter=lambda l_record: (
                                    l_record.name.startswith(
                                        l_techope_laboratory_logger.name,
                                    )
                                ),
                            )
                            __queue_listener.handlers += (
                                l_techope_laboratory_server_handler,
                            )
                    case "Windows" | "Java":
                        l_techope_laboratory_logger.warning(
                            msg="Log server not implemented for {platform}",
                            extra={
                                "platform": l_platform,
                            },
                        )
                    case _:
                        l_techope_laboratory_logger.warning(
                            msg="Unknown {platform}",
                            extra={
                                "platform": l_platform,
                            },
                        )

            # Indicates where the logs are stored.
            l_techope_laboratory_logger.info(
                msg="Logs saved in {logs_folder_path}",
                extra={
                    "logs_folder_path": str(
                        object=l_techope_laboratory_log_file_path.parent,
                    ),
                    "_to_ignore_for_stream_handler": (
                        not p_display_log_folder_path
                    ),
                },
            )


__non_word_char_pattern: Final[re.Pattern[str]] = re.compile(
    pattern=r"\W",
)


def setup_logger(
    p_name: str | None = None,
    p_stream_handler_level: int | None = logging.WARNING,
    p_log_folder_path: pathlib.Path | None = None,
    p_display_log_folder_path: bool = False,
    p_display_root_log_folder_path: bool = False,
    p_send_logs_to_server: bool = True,
) -> logging.Logger:
    """
    Configure and return a child logger of the techope_laboratory_logger.

    :param p_name: The name of the child logger. If None, uses the name of the
     folder containing the main program.
    :param p_stream_handler_level: The logging level for the console output. If
     None, no console handler is created.
    :param p_log_folder_path: Custom directory path where the log files will be
     stored. If None, searches for a local 'log' folder or falls back to the OS
     default.
    :param p_display_log_folder_path: Indicates if the path to the log folder
     must be displayed in the console.
    :param p_display_root_log_folder_path: Indicates if the path to the root log
     folder must be displayed in the console.
    :param p_send_logs_to_server: Send logs to a server. (Syslog for Linux / Not
     implemented for Windows / Not implemented for Java).
    :return: The configured child logger instance.
    """
    # Makes sure the root logger is created.
    __configure_root_logger(
        p_display_log_folder_path=p_display_root_log_folder_path,
        p_send_logs_to_server=p_send_logs_to_server,
    )

    # Retrieve the folder of the main program.
    l_main_program_folder_path: pathlib.Path = pathlib.Path(
        sys.argv[0],
    ).resolve().parent

    # Ensure a file with the name can be created.
    l_name: str = (
        # Replace characters with accents.
        "".join(
            l_char
            for l_char in unicodedata.normalize(
                "NFD",
                # Replace any non-word charactere by an underscore.
                __non_word_char_pattern.sub(
                    repl="_",
                    # Take the name passed in parameters, or the name of the
                    # folder containing the main program.
                    string=(
                        l_main_program_folder_path.name
                        if p_name is None else
                        p_name
                    ),
                ).lower(),
            ) if unicodedata.category(
                l_char,
            ) != 'Mn'
        )
    )

    l_logger: logging.Logger = logging.getLogger(
        name=".".join((
            __techope_laboratory_logger_name,
            l_name,
        )),
    )

    # Avoid log duplication if the logger is retrieved multiple times.
    with __lock:
        if not l_logger.handlers:
            l_logger.setLevel(
                level=logging.DEBUG,
            )

            l_log_folder_path: pathlib.Path
            # If a path is given in parameters, use it to store logs files.
            if p_log_folder_path is not None:
                l_log_folder_path = p_log_folder_path

            # If no path is given in parameters, search for a folder named
            # "log", "logs", "Log", or "Logs" next to the main program to use it
            # to store logs files.
            else:
                for l_log_folder_name_to_test in (
                    "log",
                    "logs",
                    "Log",
                    "Logs",
                ):
                    if l_main_program_folder_path.joinpath(
                        l_log_folder_name_to_test,
                    ).exists():
                        l_log_folder_path = l_main_program_folder_path.joinpath(
                            l_log_folder_name_to_test,
                        )
                        break
                # If none ot the previous folder is found, use the default logs
                # folder for the OS.
                else:
                    l_log_folder_path = __get_default_logs_folder_path(
                        p_application_name=l_name,
                    )

            l_log_file_path: pathlib.Path = l_log_folder_path.joinpath(
                f"{l_name}.log",
            )
            # Make sure the folder exists.
            l_log_file_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            # Creates the rotating file handler.
            l_file_handler: (
                logging.handlers.RotatingFileHandler
            ) = logging.handlers.RotatingFileHandler(
                filename=l_log_file_path,
                # 5Mo.
                maxBytes=5 * 1024 * 1024,
                backupCount=10,
                encoding=encodings.utf_8.getregentry().name,
            )
            l_file_handler.setLevel(
                level=logging.DEBUG,
            )
            l_file_handler.setFormatter(
                fmt=__CustomFileFormatter(),
            )
            l_file_handler.addFilter(
                filter=lambda l_record: l_record.name.startswith(l_logger.name),
            )

            __queue_listener.handlers += (l_file_handler,)

            # Prepare the message to indicates where the logs are stored.
            l_message: str = "Logs saved in {logs_folder_path}"
            l_extra_message_informations: dict[str, str] = {
                "logs_folder_path": str(
                    object=l_log_file_path.parent,
                ),
            }

            # if the stream handler level is not None, create a stream handler.
            if p_stream_handler_level is not None:
                l_console_handler: (
                    logging.StreamHandler[TextIO]
                ) = logging.StreamHandler(
                    stream=sys.stdout,
                )
                l_console_handler.setLevel(
                    level=p_stream_handler_level,
                )
                l_console_handler.setFormatter(
                    fmt=__CustomConsoleFormatter(),
                )
                l_console_handler.addFilter(
                    filter=lambda l_record: (
                        l_record.name == l_logger.name and not getattr(
                            l_record,
                            "_to_ignore_for_stream_handler",
                            False,
                        )
                    ),
                )

                __queue_listener.handlers += (l_console_handler,)

                # Use the logger created to indicates where the logs are stored.
                l_logger.info(
                    msg=l_message,
                    extra={
                        **l_extra_message_informations,
                        "_to_ignore_for_stream_handler": (
                            not p_display_log_folder_path
                        ),
                    },
                )

            else:
                # Use the logger created to indicates where the logs are stored.
                l_logger.info(
                    msg=l_message,
                    extra=l_extra_message_informations,
                )

    return l_logger


@atexit.register
def close_handlers() -> None:
    """Clean up all logger handlers and stop the queue listener."""
    with __log_queue.all_tasks_done:
        while __log_queue.unfinished_tasks:
            __log_queue.all_tasks_done.wait(
                timeout=2,
            )

    l_techope_laboratory_logger: logging.Logger = logging.getLogger(
        name=__techope_laboratory_logger_name,
    )

    for l_logger in (
        l_techope_laboratory_logger,
        *l_techope_laboratory_logger.getChildren(),
    ):
        for l_handler in l_logger.handlers:
            l_handler.close()

    for l_handler in __queue_listener.handlers:
        l_handler.close()

    __queue_listener.stop()
