#!/usr/bin/env python3
"""Test the module logger."""

import collections.abc
import datetime
import itertools
import json
import logging
import pathlib
import random
import re
import sys
import unittest.mock
from typing import cast

import pytest

import techope_laboratory.logger.core
from techope_laboratory.logger import setup_logger

BIG_TIMEOUT_S: int = 60


def join_queue_with_timeout(
    p_timeout_s: float = 2.0,
) -> None:
    """
    Wait for the log queue to be cleared with a timeout treshold.

    :param p_timeout_s: Timeout for the waiting.
    """
    with techope_laboratory.logger.core.__log_queue.all_tasks_done:
        while techope_laboratory.logger.core.__log_queue.unfinished_tasks:
            if not (
                techope_laboratory.logger.core.__log_queue.all_tasks_done.wait(
                    timeout=p_timeout_s,
                )
            ):
                raise TimeoutError(
                    f"The log queue was not cleared after {p_timeout_s} "
                    "seconds",
                )


@pytest.fixture
def mocked_get_default_logs_folder_path(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> unittest.mock.MagicMock:
    """
    Mock for the __get_default_logs_folder_path.

    Create a temporary folder and return a mock of the
    __get_default_logs_folder_path.

    :param tmp_path_factory: Fixture to create temporaries folders.
    :param monkeypatch: Fixture to mock variables, attributes, functions and
     methods.
    """
    l_mocked_get_default_logs_folder_path: (
        unittest.mock.MagicMock
    ) = unittest.mock.Mock(
        return_value=tmp_path_factory.mktemp(
            basename="default_logs_folder",
        ),
    )

    monkeypatch.setattr(
        target=techope_laboratory.logger.core,
        name="__get_default_logs_folder_path",
        value=l_mocked_get_default_logs_folder_path,
    )

    return l_mocked_get_default_logs_folder_path


@pytest.fixture(
    autouse=True,
)
def reset_root_logger_after_test() -> collections.abc.Generator[None]:
    """Reset the root logger after a test."""
    yield

    join_queue_with_timeout(
        p_timeout_s=BIG_TIMEOUT_S,
    )

    l_techope_laboratory_logger: logging.Logger = logging.getLogger(
        name=techope_laboratory.logger.core.__techope_laboratory_logger_name,
    )

    for l_logger in (
        l_techope_laboratory_logger,
        *l_techope_laboratory_logger.getChildren(),
    ):
        for l_handler in l_logger.handlers[:]:
            l_handler.close()
            l_logger.removeHandler(
                hdlr=l_handler,
            )

    for l_handler in techope_laboratory.logger.core.__queue_listener.handlers:
        l_handler.close()
    techope_laboratory.logger.core.__queue_listener.handlers = ()

    techope_laboratory.logger.core.__queue_listener.stop()


@pytest.fixture
def mocked_main_script_path(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Mock the sys.argv[0] value.

    Create a temporary folder to mock the main script file path returned by the
    sys.argv[0] value.

    :param tmp_path_factory: Fixture to create temporaries folders.
    :param monkeypatch: Fixture to mock variables, attributes, functions and
     methods.
    """
    l_mocked_main_script_file_path: pathlib.Path = tmp_path_factory.mktemp(
        basename="mocked_main_script_folder",
    ).joinpath(
        "mocked_main_script.py",
    )

    monkeypatch.setattr(
        target=sys,
        name="argv",
        value=[str(l_mocked_main_script_file_path)],
    )


def test_root_logger_path(
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
) -> None:
    """
    Test the root logger configuration.

    The __get_default_logs_folder_path should be called only once and the
    rotating file should be created in the right folder.

    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    """
    techope_laboratory.logger.core.__configure_root_logger()
    mocked_get_default_logs_folder_path.assert_called_once_with(
        p_application_name=techope_laboratory.logger.core.__application_name,
        p_author_name=techope_laboratory.logger.core.__author_name,
    )

    l_expected_log_file_path: (
        pathlib.Path
    ) = mocked_get_default_logs_folder_path().joinpath(
        f"{techope_laboratory.logger.core.__techope_laboratory_logger_name}"
        ".log",
    )
    assert l_expected_log_file_path == pathlib.Path(next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and (
            techope_laboratory.logger.core.__techope_laboratory_logger_name in
            l_handler.baseFilename
        ),
        techope_laboratory.logger.core.__queue_listener.handlers,
    )).baseFilename)

    join_queue_with_timeout()
    assert l_expected_log_file_path.exists()


def test_first_log_from_root_logger(
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Test the root logger configuration.

    Check the log recorded in the rotating file and in the console when the root
    logger is configuring.

    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    :param capsys: Fixture to capture std.out et std.err.
    """
    l_log_datetime_min: datetime.datetime = datetime.datetime.now(
        tz=datetime.UTC,
    )
    techope_laboratory.logger.core.__configure_root_logger(
        p_display_log_folder_path=True,
    )
    l_log_datetime_max: datetime.datetime = datetime.datetime.now(
        tz=datetime.UTC,
    )

    join_queue_with_timeout()
    l_captured = capsys.readouterr()
    assert not len(l_captured.err)

    l_techope_laboratory_logger: logging.Logger = logging.getLogger(
        name=techope_laboratory.logger.core.__techope_laboratory_logger_name,
    )
    l_log_file_path: pathlib.Path = pathlib.Path(next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and l_techope_laboratory_logger.name in l_handler.baseFilename,
        techope_laboratory.logger.core.__queue_listener.handlers,
    )).baseFilename)

    l_file_path: pathlib.Path | None = None
    for l_content, l_source in (
        (l_log_file_path.read_text(), "file"),
        (l_captured.out, "console"),
    ):
        l_log_lines: list[str] = l_content.splitlines()
        assert len(l_log_lines) == 1

        l_log_line: str = l_log_lines[0]
        if l_source == "file":
            l_log_json: dict[str, str | int] = json.loads(
                s=l_log_line,
            )
        elif l_source == "console":
            l_first_index: int = l_log_line.find("{")
            l_last_index: int = l_log_line.rfind("}")
            l_log_json: dict[str, str | int] = json.loads(
                s=l_log_line[l_first_index:l_last_index+1],
            )
        else:
            raise ValueError(
                f"Unknown source: {l_source}"
            )

        assert l_log_datetime_min < datetime.datetime.fromisoformat(
            cast(
                typ=str,
                val=l_log_json["timestamp"],
            ),
        ) < l_log_datetime_max

        assert l_log_json["level"] == logging.getLevelName(
            level=logging.INFO,
        )
        assert l_log_json["logger"] == l_techope_laboratory_logger.name

        if l_source == "file":
            assert (
                "file_path" in l_log_json and
                isinstance(l_log_json["file_path"], str)
            )
            if l_file_path is not None:
                assert pathlib.Path(
                    l_log_json["file_path"],
                ).stem == l_file_path.stem
            else:
                l_file_path = pathlib.Path(
                    l_log_json["file_path"],
                )
        elif l_source == "console":
            assert (
                "module" in l_log_json and
                isinstance(l_log_json["module"], str)
            )
            if l_file_path is not None:
                assert pathlib.Path(
                    l_log_json["module"],
                ).stem == l_file_path.stem
            else:
                l_file_path = pathlib.Path(
                    l_log_json["module"],
                )
        else:
            raise ValueError(
                f"Unknown source: {l_source}",
            )

        if l_source == "file":
            assert (
                "function" in l_log_json and
                isinstance(l_log_json["function"], str)
            )
        elif l_source == "console":
            pass
        else:
            raise ValueError(
                f"Unknown source: {l_source}",
            )

        assert "line" in l_log_json and isinstance(l_log_json["line"], int)
        l_logs_folder_path_key: str = "logs_folder_path"
        assert l_log_json["message"] == (
            f"Logs saved in {{{l_logs_folder_path_key}}}"
        )
        assert l_log_json[l_logs_folder_path_key] == str(l_log_file_path.parent)


def test_no_console_log_on_root_logger_configuration(
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Test no log is recorded in the console when the root logger is configuring.

    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    :param capsys: Fixture to capture std.out et std.err.
    """
    techope_laboratory.logger.core.__configure_root_logger()

    join_queue_with_timeout()
    l_captured = capsys.readouterr()

    assert not len(l_captured.err)
    assert not len(l_captured.out)


def test_default_logs_folder_path_on_new_logger_creation(
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
    mocked_main_script_path: None,
) -> None:
    """
    Test new logger configuration.

    Test __get_default_logs_folder_path is call exactly twice when a new logger
    is configuring (without specifying a name) and the rotating file is created
    in the right folder.

    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    :param mocked_main_script_path: Fixture to mock the main script file path
     returned by sys.argv[0].
    """
    l_new_logger: logging.Logger = setup_logger()
    l_main_script_folder_name: str = pathlib.Path(
        sys.argv[0],
    ).parent.name
    mocked_get_default_logs_folder_path.assert_has_calls(
        calls=(
            unittest.mock.call(
                p_application_name=(
                    techope_laboratory.logger.core.__application_name
                ),
                p_author_name=techope_laboratory.logger.core.__author_name,
            ),
            unittest.mock.call(
                p_application_name=l_main_script_folder_name,
            ),
        ),
    )

    l_expected_log_file_path: (
        pathlib.Path
    ) = mocked_get_default_logs_folder_path().joinpath(
        f"{l_main_script_folder_name}.log",
    )
    assert l_expected_log_file_path == pathlib.Path(next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and l_new_logger.name.split(
            sep=".",
        )[-1] in l_handler.baseFilename,
        techope_laboratory.logger.core.__queue_listener.handlers,
    )).baseFilename)

    join_queue_with_timeout()
    assert l_expected_log_file_path.exists()


def test_default_logs_folder_path_on_new_logger_creation_with_name(
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
    mocked_main_script_path: None,
) -> None:
    """
    Test new logger configuration.

    Test __get_default_logs_folder_path is call exactly twice when a new logger
    is configuring (with a name specified) and the rotating file is created in
    the right folder.

    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    :param mocked_main_script_path: Fixture to mock the main script file path
     returned by sys.argv[0].
    """
    l_logger_name: str = "a_random_name"
    l_new_logger: logging.Logger = setup_logger(
        p_name=l_logger_name,
    )
    mocked_get_default_logs_folder_path.assert_has_calls(
        calls=(
            unittest.mock.call(
                p_application_name=(
                    techope_laboratory.logger.core.__application_name
                ),
                p_author_name=techope_laboratory.logger.core.__author_name,
            ),
            unittest.mock.call(
                p_application_name=l_logger_name,
            ),
        ),
    )

    l_expected_log_file_path: (
        pathlib.Path
    ) = mocked_get_default_logs_folder_path().joinpath(
        f"{l_logger_name}.log",
    )
    assert l_expected_log_file_path == pathlib.Path(next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and l_new_logger.name.split(
            sep=".",
        )[-1] in l_handler.baseFilename,
        techope_laboratory.logger.core.__queue_listener.handlers,
    )).baseFilename)

    join_queue_with_timeout()
    assert l_expected_log_file_path.exists()


@pytest.mark.parametrize(
    "p_log_folder_name, p_logger_name", tuple(itertools.product(
        ("log", "logs", "Log", "Logs"),
        (None, "a_random_name"),
    )),
)
def test_logs_folder_path_on_new_logger_creation_log_folder_existing(
    p_log_folder_name: str,
    p_logger_name: str | None,
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
    mocked_main_script_path: None,
) -> None:
    """
    Test new logger configuration.

    Test the rotating file is created in the right folder when a log folder
    exists beside the main program.

    :param p_log_folder_name: Folder name for logs beside the main program.
    :param p_logger_name: The logger name.
    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    :param mocked_main_script_path: Fixture to mock the main script file path
     returned by sys.argv[0].
    """
    l_expected_log_folder_path: pathlib.Path = pathlib.Path(
        sys.argv[0]
    ).parent.joinpath(
        p_log_folder_name,
    )
    l_expected_log_folder_path.mkdir()

    l_logger_name: str = (
        pathlib.Path(
            sys.argv[0],
        ).parent.name
        if p_logger_name is None else
        p_logger_name
    )

    l_new_logger: logging.Logger = setup_logger(
        p_name=p_logger_name,
    )
    mocked_get_default_logs_folder_path.assert_called_once_with(
        p_application_name=techope_laboratory.logger.core.__application_name,
        p_author_name=techope_laboratory.logger.core.__author_name,
    )

    l_expected_log_file_path: (
        pathlib.Path
    ) = l_expected_log_folder_path.joinpath(
        f"{l_logger_name}.log",
    )
    assert l_expected_log_file_path == pathlib.Path(next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and l_new_logger.name.split(
            sep=".",
        )[-1] in l_handler.baseFilename,
        techope_laboratory.logger.core.__queue_listener.handlers,
    )).baseFilename)

    join_queue_with_timeout()
    assert l_expected_log_file_path.exists()


@pytest.mark.parametrize(
    "p_logger_name", (
        None,
        "a_random_name",
    ),
)
def test_logs_folder_path_on_new_logger_creation_log_folder_given(
    p_logger_name: str | None,
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
    mocked_main_script_path: None,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """
    Test new logger configuration.

    Test the rotating file is created in the right folder when a log folder is
    given in parameters.

    :param p_logger_name: The logger name.
    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    :param mocked_main_script_path: Fixture to mock the main script file path
     returned by sys.argv[0].
    :param tmp_path_factory: Fixture to create temporaries folders.
    """
    l_expected_log_folder_path: pathlib.Path = tmp_path_factory.mktemp(
        basename="created_log_folder_path",
    )

    l_logger_name: str = (
        pathlib.Path(
            sys.argv[0],
        ).parent.name
        if p_logger_name is None else
        p_logger_name
    )

    l_new_logger: logging.Logger = setup_logger(
        p_name=p_logger_name,
        p_log_folder_path=l_expected_log_folder_path,
    )
    mocked_get_default_logs_folder_path.assert_called_once_with(
        p_application_name=techope_laboratory.logger.core.__application_name,
        p_author_name=techope_laboratory.logger.core.__author_name,
    )

    l_expected_log_file_path: (
        pathlib.Path
    ) = l_expected_log_folder_path.joinpath(
        f"{l_logger_name}.log",
    )
    assert l_expected_log_file_path == pathlib.Path(next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and l_new_logger.name.split(
            sep=".",
        )[-1] in l_handler.baseFilename,
        techope_laboratory.logger.core.__queue_listener.handlers,
    )).baseFilename)

    join_queue_with_timeout()
    assert l_expected_log_file_path.exists()


@pytest.mark.parametrize(
    "p_stream_handler_level", (
        None,
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ),
)
def test_new_logger_has_stream_handler(
    p_stream_handler_level: int | None,
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
    mocked_main_script_path: None,
) -> None:
    """
    Test the creation of a stream handler or not on a creation of a new logger.

    :param p_stream_handler_level: The logging level for the console output. If
     None, no console handler is created.
    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    :param mocked_main_script_path: Fixture to mock the main script file path
     returned by sys.argv[0].
    """
    setup_logger(
        p_stream_handler_level=p_stream_handler_level,
    )

    assert len(tuple(
        l_handler
        for l_handler in (
            techope_laboratory.logger.core.__queue_listener.handlers
        ) if type(l_handler) is logging.StreamHandler
    )) == int(p_stream_handler_level is not None) + 1


@pytest.mark.parametrize(
    (
        "p_stream_handler_level, "
        "p_display_log_folder_path, "
        "p_display_root_log_folder_path"
    ), tuple(itertools.product(
        (
            None,
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ),
        (True, False),
        (True, False),
    )),
)
def test_display_logs_folders(
    p_stream_handler_level: int | None,
    p_display_log_folder_path: bool,
    p_display_root_log_folder_path: bool,
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
    mocked_main_script_path: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Test the logs recorded in the console when another logger is configuring.

    :param p_stream_handler_level: The logging level for the console output. If
     None, no console handler is created.
    :param p_display_log_folder_path: Indicates if the log path should be
     displayed.
    :param p_display_root_log_folder_path: Indicates if the root log path should
     be displayed.
    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    :param mocked_main_script_path: Fixture to mock the main script file path
     returned by sys.argv[0].
    :param capsys: Fixture to capture std.out et std.err.
    """
    setup_logger(
        p_stream_handler_level=p_stream_handler_level,
        p_display_log_folder_path=p_display_log_folder_path,
        p_display_root_log_folder_path=p_display_root_log_folder_path,
    )

    join_queue_with_timeout()
    l_captured = capsys.readouterr()
    assert not len(l_captured.err)

    l_nb_expected_line = int(p_display_root_log_folder_path)
    l_nb_expected_line += int(
        p_display_log_folder_path and
        p_stream_handler_level is not None and
        p_stream_handler_level <= logging.INFO
    )
    assert len(l_captured.out.splitlines()) == l_nb_expected_line


def test_first_logs_from_new_logger_and_root_logger(
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
    mocked_main_script_path: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Test new logger configuration.

    Test the log recorded in the rotating file and the console when a new logger
    is configuring.

    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    :param mocked_main_script_path: Fixture to mock the main script file path
     returned by sys.argv[0].
    :param capsys: Fixture to capture std.out et std.err.
    """
    l_log_datetime_min: datetime.datetime = datetime.datetime.now(
        tz=datetime.UTC,
    )
    l_new_logger: logging.Logger = setup_logger(
        p_name="a_random_name",
        p_stream_handler_level=logging.INFO,
        p_display_log_folder_path=True,
        p_display_root_log_folder_path=True,
    )
    l_log_datetime_max: datetime.datetime = datetime.datetime.now(
        tz=datetime.UTC,
    )

    join_queue_with_timeout()
    l_captured = capsys.readouterr()
    assert not len(l_captured.err)

    l_root_log_file_path: pathlib.Path = pathlib.Path(next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and (
            techope_laboratory.logger.core.__techope_laboratory_logger_name in
            l_handler.baseFilename
        ),
        techope_laboratory.logger.core.__queue_listener.handlers,
    )).baseFilename)

    l_log_file_path: pathlib.Path = pathlib.Path(next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and l_new_logger.name.split(
            sep=".",
        )[-1] in l_handler.baseFilename,
        techope_laboratory.logger.core.__queue_listener.handlers,
    )).baseFilename)

    l_file_path: pathlib.Path | None = None
    for l_content, l_source, l_is_root in (
        (l_log_file_path.read_text(), "file", False),
        (l_root_log_file_path.read_text(), "file", True),
        (l_captured.out, "console", None),
    ):
        l_log_lines: list[str] = l_content.splitlines()
        assert len(l_log_lines) == (
            1
            if l_source == "file" and not l_is_root else
            2
        )

        l_log_line: str = l_log_lines[-1]
        if l_source == "file":
            l_log_json: dict[str, str | int] = json.loads(
                s=l_log_line,
            )
        elif l_source == "console":
            l_first_index: int = l_log_line.find("{")
            l_last_index: int = l_log_line.rfind("}")
            l_log_json: dict[str, str | int] = json.loads(
                s=l_log_line[l_first_index:l_last_index+1],
            )
        else:
            raise ValueError(
                f"Unknown source: {l_source}",
            )

        assert l_log_datetime_min < datetime.datetime.fromisoformat(
            cast(
                typ=str,
                val=l_log_json["timestamp"],
            ),
        ) < l_log_datetime_max

        assert l_log_json["level"] == logging.getLevelName(
            level=logging.INFO,
        )
        assert l_log_json["logger"] == l_new_logger.name

        if l_source == "file":
            assert (
                "file_path" in l_log_json and
                isinstance(l_log_json["file_path"], str)
            )
            if l_file_path is not None:
                assert pathlib.Path(
                    l_log_json["file_path"],
                ).stem == l_file_path.stem
            else:
                l_file_path = pathlib.Path(
                    l_log_json["file_path"],
                )
        elif l_source == "console":
            assert (
                "module" in l_log_json and
                isinstance(l_log_json["module"], str)
            )
            if l_file_path is not None:
                assert pathlib.Path(
                    l_log_json["module"],
                ).stem == l_file_path.stem
            else:
                l_file_path = pathlib.Path(
                    l_log_json["module"],
                )
        else:
            raise ValueError(
                f"Unknown source: {l_source}",
            )

        if l_source == "file":
            assert (
                "function" in l_log_json and
                isinstance(l_log_json["function"], str)
            )
        elif l_source == "console":
            pass
        else:
            raise ValueError(
                f"Unknown source: {l_source}",
            )

        assert "line" in l_log_json and isinstance(l_log_json["line"], int)
        l_logs_folder_path_key: str = "logs_folder_path"
        assert l_log_json["message"] == (
            f"Logs saved in {{{l_logs_folder_path_key}}}"
        )
        assert l_log_json[l_logs_folder_path_key] == str(l_log_file_path.parent)


def random_char_generator(
    p_nb_char: int,
) -> str:
    """
    Generate random lowers characteres.

    :param p_nb_char: Nb characteres to get in the returned string.
    :return: A string with <p_nb_char> random lower characteres.
    """
    return "".join(
        map(
            chr,
            random.choices(
                population=range(ord("a"), ord("z") + 1),
                k=p_nb_char,
            ),
        ),
    )

def fill_a_file_log(
    p_logger: logging.Logger,
    p_nb_line_to_write: int = 10,
) -> None:
    """
    Fill the log file at maximum.

    :param p_logger: Logger to use to fill the file.
    :param p_nb_line_to_write: Number of line to write in the file.
    """
    l_rotating_file_handler: logging.handlers.RotatingFileHandler = next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and p_logger.name.split(
            sep=".",
        )[-1] in l_handler.baseFilename,
        techope_laboratory.logger.core.__queue_listener.handlers,
    ))
    l_size_max_octets: int = l_rotating_file_handler.maxBytes
    l_log_file_path: pathlib.Path = pathlib.Path(
        l_rotating_file_handler.baseFilename,
    )

    join_queue_with_timeout(
        p_timeout_s=BIG_TIMEOUT_S,
    )
    l_file_size_before_log_octets: int = l_log_file_path.stat().st_size
    p_logger.debug(
        msg=random_char_generator(
            p_nb_char=1,
        ),
    )
    join_queue_with_timeout()
    l_file_size_after_log_octets: int = l_log_file_path.stat().st_size
    p_nb_line_to_write -= 1
    l_line_size_octets: int = (
        l_file_size_after_log_octets - l_file_size_before_log_octets - 1
    )

    l_nb_octets_to_write: int = l_size_max_octets - l_file_size_after_log_octets
    l_nb_octets_to_write -= 1
    assert l_nb_octets_to_write >= l_line_size_octets * p_nb_line_to_write

    for _ in range(p_nb_line_to_write - 1):
        p_logger.debug(
            msg=random_char_generator(
                p_nb_char=l_nb_octets_to_write // p_nb_line_to_write,
            ),
        )
        join_queue_with_timeout(
            p_timeout_s=BIG_TIMEOUT_S,
        )

    l_file_size_after_log_octets: int = l_log_file_path.stat().st_size
    p_logger.debug(
        msg=random_char_generator(
            p_nb_char=(
                l_size_max_octets - l_file_size_after_log_octets -
                l_line_size_octets - 1
            ),
        ),
    )


def test_log_rotation(
    mocked_get_default_logs_folder_path: unittest.mock.MagicMock,
) -> None:
    """
    Test log rotation.

    Test the rotation is done when the limit size is reached and files name are
    those expected.

    :param mocked_get_default_logs_folder_path: The mock function replacing the
     function __get_default_logs_folder_path.
    """
    l_logger_name: str = "a_random_name"
    l_new_logger: logging.Logger = setup_logger(
        p_name=l_logger_name,
        p_send_logs_to_server=False,
    )
    l_rotating_file_handler: logging.handlers.RotatingFileHandler = next(filter(
        lambda l_handler: isinstance(
            l_handler,
            logging.handlers.RotatingFileHandler,
        ) and l_new_logger.name.split(
            sep=".",
        )[-1] in l_handler.baseFilename,
        techope_laboratory.logger.core.__queue_listener.handlers,
    ))
    l_main_log_file_path: pathlib.Path = pathlib.Path(
        l_rotating_file_handler.baseFilename,
    )

    # Fill the first file.
    fill_a_file_log(
        p_logger=l_new_logger,
    )

    join_queue_with_timeout(
        p_timeout_s=BIG_TIMEOUT_S,
    )
    l_log_file_paths: list[pathlib.Path] = [
        l_file_path
        for l_file_path in l_main_log_file_path.parent.iterdir()
        if l_logger_name in l_file_path.name
    ]
    assert len(l_log_file_paths) == 1
    assert l_log_file_paths[0] == l_main_log_file_path
    assert (
        l_rotating_file_handler.maxBytes -l_main_log_file_path.stat().st_size
    ) == 1

    # Should create one backup file.
    l_new_logger.debug(
        msg="The too much message",
    )

    join_queue_with_timeout()
    l_log_file_paths = [
        l_file_path
        for l_file_path in l_main_log_file_path.parent.iterdir()
        if l_logger_name in l_file_path.name
    ]
    assert len(l_log_file_paths) == 2
    assert l_main_log_file_path in l_log_file_paths
    l_log_file_paths.remove(l_main_log_file_path)
    assert re.compile(
        pattern=r"_".join((
            l_main_log_file_path.stem,
        )) + r"\.log.\d+",
    ).fullmatch(
        string=l_log_file_paths[0].name
    )

    # Fill the log file and create many backup files.
    for _ in range(l_rotating_file_handler.backupCount + 2):
        fill_a_file_log(
            p_logger=l_new_logger,
        )
        l_new_logger.debug(
            msg="The too much message",
        )

    join_queue_with_timeout(
        p_timeout_s=BIG_TIMEOUT_S,
    )
    l_log_file_paths = [
        l_file_path
        for l_file_path in l_main_log_file_path.parent.iterdir()
        if l_logger_name in l_file_path.name
    ]
    assert len(l_log_file_paths) == l_rotating_file_handler.backupCount + 1
    assert l_main_log_file_path in l_log_file_paths
    l_log_file_paths.remove(l_main_log_file_path)
    for l_file_path in l_log_file_paths:
        assert re.compile(
            pattern=r"_".join((
                l_main_log_file_path.stem,
            )) + r"\.log.\d+",
        ).fullmatch(
            string=l_file_path.name
        )
