#!/usr/bin/env python3
# coding: utf-8
"""Tests file for the module counter_naming."""
import encodings.utf_8
import pathlib
import random
import re

import pytest

from techope_laboratory.counter_naming import (
    DEFAULT_COUNTER_KEY_PATTERN,
    DEFAULT_COUNTER_PATTERN,
    default_counter_to_ints,
    get_default_counter_pattern,
    get_max_counter_element,
    get_new_counter,
    sort_by_counter,
)


def test_get_default_counter_pattern() -> None:
    """Check the generation of the default pattern."""
    pattern: re.Pattern[str] = get_default_counter_pattern()
    assert isinstance(pattern, re.Pattern)
    assert (
        pattern.pattern == rf"(?P<{DEFAULT_COUNTER_KEY_PATTERN}>(?:\d+\.)*\d+)"
    )
    assert pattern.pattern == DEFAULT_COUNTER_PATTERN.pattern
    other_pattern: re.Pattern[str] = get_default_counter_pattern(
        p_pattern_key="something_else",
    )
    assert other_pattern.pattern == pattern.pattern.replace(
        DEFAULT_COUNTER_KEY_PATTERN, "something_else",
    )


@pytest.mark.parametrize(
    "p_input_data, p_expected_counter", (
        ("1.2.3", (1, 2, 3)),
        ("10.20", (10, 20)),
        ("158.machine.33", (158, 33)),
        ("5", (5,)),
        ("invalid.1.2", (1, 2)),
        ("", tuple()),
    ),
)
def test_default_counter_to_ints(
    p_input_data: str,
    p_expected_counter: tuple[int, ...],
) -> None:
    """Check the conversion of a counter to a tuple of integers."""
    assert default_counter_to_ints(p_input_data) == p_expected_counter


@pytest.mark.parametrize(
    "p_input_data, p_pattern, p_expected_sort", (
        (
            ["file_1.2.txt", "file_1.10.txt", "file_1.1.txt", "other_file.txt"],
            rf"^file_{DEFAULT_COUNTER_PATTERN.pattern}\.txt$",
            ["file_1.1.txt", "file_1.2.txt", "file_1.10.txt"],
        ),
        (
            [b"archive_2.0.tar", b"archive_1.5.tar", b"archive_2.10.tar"],
            rf"^archive_{DEFAULT_COUNTER_PATTERN.pattern}\.tar$".encode(
                encoding=encodings.utf_8.getregentry().name,
            ),
            [b"archive_1.5.tar", b"archive_2.0.tar", b"archive_2.10.tar"],
        ),
    ),
)
def test_sort_by_counter[T: (str, bytes)](
    p_input_data: list[T],
    p_pattern: T,
    p_expected_sort: list[T],
) -> None:
    """
    Check the correct sorting of standard stringsor bytes with multi-level
    counters.
    """
    random.shuffle(
        x=p_input_data,
    )
    assert list(
        match.string
        for match in sort_by_counter(
            p_input_data,
            p_item_pattern=re.compile(
                pattern=p_pattern,
            ),
        )
    ) == p_expected_sort, f"Shuffled data: {p_input_data}"


@pytest.mark.parametrize(
    "p_input_data, p_pattern, p_expected_sort", (
        (
            ["file_1.2.txt", "file_1.10.txt", "file_1.1.txt", "other_file.txt"],
            rf"^file_{DEFAULT_COUNTER_PATTERN.pattern}\.txt$",
            ["file_1.1.txt", "file_1.2.txt", "file_1.10.txt"],
        ),
    ),
)
def test_sort_by_counter_in_directory(
    p_input_data: list[str],
    p_pattern: str,
    p_expected_sort: list[str],
    tmp_path: pathlib.Path,
) -> None:
    """
    Check the correct sorting of standard strings with multi-level counters
    in a directory.
    """
    random.shuffle(
        x=p_input_data,
    )
    for file_name in p_input_data:
        tmp_path.joinpath(
            file_name,
        ).touch()

    assert list(
        match.string
        for match in sort_by_counter(
            p_data=(
                file_path.name
                for file_path in tmp_path.iterdir()
            ),
            p_item_pattern=re.compile(
                pattern=p_pattern,
            ),
        )
    ) == p_expected_sort, f"Shuffled data: {p_input_data}"


@pytest.mark.parametrize(
    "p_input_data, p_pattern, p_expected_counter", (
        (
            ["doc_1.txt", "doc_2.txt"],
            rf"^doc_{DEFAULT_COUNTER_PATTERN.pattern}\.txt$",
            (3,),
        ),
        (
            ["report_1.2.3.pdf", "report_1.2.4.pdf"],
            rf"^report_{DEFAULT_COUNTER_PATTERN.pattern}\.pdf$",
            (1, 2, 5),
        ),
        (
            [],
            rf"^anything_{DEFAULT_COUNTER_PATTERN.pattern}\.ext$",
            (1,),
        ),
        (
            ["no_match.txt"],
            rf"^no_{DEFAULT_COUNTER_PATTERN.pattern}\.txt$",
            (1,),
        ),
        (
            ["doc_1.txt", "doc_4.txt"],
            rf"^doc_{DEFAULT_COUNTER_PATTERN.pattern}\.txt$",
            (5,),
        ),
    ),
)
def test_get_new_counter[T: (str, bytes)](
    p_input_data: list[T],
    p_pattern: T,
    p_expected_counter: tuple[int, ...],
) -> None:
    """
    Check the calculation of the next counter on different formats and edge
    cases.
    """
    assert get_new_counter(
        p_data=p_input_data,
        p_item_pattern=re.compile(
            pattern=p_pattern,
        ),
     ) == p_expected_counter


@pytest.mark.parametrize(
    "p_input_data, p_pattern, p_expected_counter", (
        (
            ["img_0.9.png", "img_1.4.png", "img_1.3.png"],
            rf"^img_{DEFAULT_COUNTER_PATTERN.pattern}\.png$",
            "img_1.4.png",
        ),
        (
            ["invalide_name.png"],
            rf"^img_{DEFAULT_COUNTER_PATTERN.pattern}\.png$",
            ValueError("No element in the list matches the given pattern"),
        ),
    ),
)
def test_get_max_counter_element[T: (str, bytes)](
    p_input_data: list[T],
    p_pattern: T,
    p_expected_counter: T | Exception,
) -> None:
    """Check the retrieval of the element with the highest counter."""
    if isinstance(p_expected_counter, Exception):
        with pytest.raises(
            expected_exception=type(p_expected_counter),
            match=p_expected_counter.args[0],
        ):
            get_max_counter_element(
                p_data=p_input_data,
                p_item_pattern=re.compile(
                    pattern=p_pattern,
                ),
            )
    else:
        assert get_max_counter_element(
            p_data=p_input_data,
            p_item_pattern=re.compile(
                pattern=p_pattern,
            ),
        ) == p_expected_counter
