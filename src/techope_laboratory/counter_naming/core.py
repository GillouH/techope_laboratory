#!/usr/bin/env python3
# coding: utf-8
"""
This module defines tools that facilitate the sorting of elements by counter.
"""
import encodings.utf_8
import re
import typing

DEFAULT_COUNTER_KEY_PATTERN: typing.Final[str] = "counter"


def get_default_counter_pattern(
        p_pattern_key: None | str = DEFAULT_COUNTER_KEY_PATTERN,
) -> re.Pattern[str]:
    """
    This function allows you to retrieve the default pattern for a counter,
    using the pattern key provided as a parameter.

    Example :
        - "3"
        - "489"
        - "4569.54"
        - "5.6"
        - "14964.186.4786.5.4186

    :param p_pattern_key: The pattern key to use.
    :return: The default pattern for a counter.
    """
    return re.compile(
        pattern=rf"(?P<{p_pattern_key}>(?:\d+\.)*\d+)",
    )


DEFAULT_COUNTER_PATTERN: re.Pattern[str] = get_default_counter_pattern()


def default_counter_to_ints[T: (str, bytes)](
        p_counter: T,
) -> tuple[int, ...]:
    """
    This is the default function to convert a counter (str) to a tuple of int.

    :param p_counter: The counter.
    :return: Tuple of int representing the counter.
    """
    l_counter: str = typing.cast(
        typ=str,
        val=(
            p_counter
            if isinstance(p_counter, str) else
            p_counter.decode(
                encoding=encodings.utf_8.getregentry().name,
            )
        ),
    )

    return tuple(
        int(number_str)
        for number_str in l_counter.split(
            sep=".",
        ) if number_str.isdigit()
    )


def sort_by_counter[T: (str, bytes)](
        p_data: typing.Iterable[T],
        p_item_pattern: re.Pattern[T],
        p_counter_key_pattern: str = DEFAULT_COUNTER_KEY_PATTERN,
        p_func_counter_to_ints: typing.Callable[[T], tuple[int, ...]] = (
                default_counter_to_ints
        ),
        p_reverse: bool = False,
) -> list[re.Match[T]]:
    """
    This function sorts a list of data based on the counter associated with each
    item.

    The counter for each item is retrieved using `<p_item_pattern>` and the
    named group specified by `<p_counter_key_pattern>`. If an item does not
    match the pattern, it is ignored and will not be included in the returned
    list.

    Detailed explanation of the function's processing:
        1 - Apply the `<p_item_pattern>` to each item in `<p_data>`.
        2 - Filter out items that do not match the pattern.
        3 - Retrieve the named group defined by `<p_counter_key_pattern>` for
            each item that matches the pattern.
        4 - Convert the string value from the named group into a tuple of
            integers for each matching item.
        5 - Sort the matching items based on this tuple of integers.
            - In the simplest case, the result is a tuple containing a single
              integer; the sorting is then based on that integer.
            - If the result is a tuple containing multiple integers, the sorting
              is performed based on the integer at index 0; if those are equal,
              it proceeds to the next index, and so on.
            - If `<p_reverse>` is set to `True`, the sort order is reversed.

    :param p_data: The collection of data to be sorted by counter.
    :param p_item_pattern: The regular expression pattern that each item in
     <p_data> must match. This pattern must define a named group specified by
     <p_counter_key_pattern>.
    :param p_counter_key_pattern: The name of the named group to extract from
     the regular expression <p_item_pattern>.
    :param p_func_counter_to_ints: A function allowing to transform the string
     retrieved from the named group <p_counter_key_pattern> into a tuple of
     integers used for sorting the items.
    :param p_reverse: Indicates whether the sort order should be reversed.
    :return: A list of re.Match objects from <p_data> sorted by counter.
    """
    # 1 - Apply the `<p_item_pattern>` to each item in `<p_data>`.
    # 2 - Filter out items that do not match the pattern.
    matches: list[re.Match[T]] = list(
        match
        for item in p_data
        if (match := p_item_pattern.match(
            string=item,
        )) is not None
    )

    # 5 - Sort the matching items based on this tuple of integers.
    return sorted(
        matches,
        # 4 - Convert the string value from the named group into a tuple of
        #     integers for each matching item.
        key=lambda match: p_func_counter_to_ints(
            # 3 - Retrieve the named group defined by `<p_counter_key_pattern>`
            #     for each item that matches the pattern.
            typing.cast(
                typ=T,
                val=match[p_counter_key_pattern],
            ),
        ),
        reverse=p_reverse,
    )


def get_new_counter[T: (str, bytes)](
        p_data: typing.Iterable[T],
        p_item_pattern: re.Pattern[T],
        p_counter_key_pattern: str = DEFAULT_COUNTER_KEY_PATTERN,
        p_func_counter_to_ints: typing.Callable[[T], tuple[int, ...]] = (
                default_counter_to_ints
        ),
) -> tuple[int, ...]:
    """
    This function determines the numbers for a new counter based on a list of
    data entries that include a counter.

    :param p_data: The collection of data entries containing a counter.
    :param p_item_pattern: The regular expression pattern that must be matched
     by the elements in <p_data> to be considered. This pattern must define a
     named group specified by <p_counter_key_pattern>.
    :param p_counter_key_pattern: The name of the group to be extracted from
     the regular expression <p_item_pattern>.
    :param p_func_counter_to_ints: A function that converts the string
     extracted from the named group <p_counter_key_pattern> into a tuple of
     integers, which is then used to sort the elements.
    :return: A tuple representing the next counter value to be used within
     <p_data>.
    """
    sorted_matches: list[re.Match[T]] = sort_by_counter(
        p_data=p_data,
        p_item_pattern=p_item_pattern,
        p_counter_key_pattern=p_counter_key_pattern,
        p_func_counter_to_ints=p_func_counter_to_ints,
        p_reverse=True,
    )

    max_counter_str: T = (
        typing.cast(
            typ=T,
            val=sorted_matches[0][p_counter_key_pattern],
        )
        if len(sorted_matches) else
        typing.cast(
            typ=T,
            val="0",
        )
    )

    max_counter_tuple: tuple[int, ...] = p_func_counter_to_ints(
        max_counter_str,
    )
    return (
        max_counter_tuple[:-1] + (max_counter_tuple[-1] + 1,)
        if max_counter_tuple else
        (1,)
    )


def get_max_counter_element[T: (str, bytes)](
        p_data: typing.Iterable[T],
        p_item_pattern: re.Pattern[T],
        p_counter_key_pattern: str = DEFAULT_COUNTER_KEY_PATTERN,
        p_func_counter_to_ints: typing.Callable[[T], tuple[int, ...]] = (
                default_counter_to_ints
        ),
) -> T:
    """
    This function retrieves the element with the highest counter from a list of
    data entries that include a counter.

    :param p_data: The collection of data entries containing a counter.
    :param p_item_pattern: The regular expression pattern that must be matched
     by the elements in <p_data> to be considered. This pattern must define a
     named group specified by <p_counter_key_pattern>.
    :param p_counter_key_pattern: The name of the group to be extracted from
     the regular expression <p_item_pattern>.
    :param p_func_counter_to_ints: A function that converts the string
     extracted from the named group <p_counter_key_pattern> into a tuple of
     integers, which is then used to sort the elements.
    :return: The element with the highest counter in <p_data>.
    """
    sorted_matches: list[re.Match[T]] = sort_by_counter(
        p_data=p_data,
        p_item_pattern=p_item_pattern,
        p_counter_key_pattern=p_counter_key_pattern,
        p_func_counter_to_ints=p_func_counter_to_ints,
        p_reverse=True,
    )

    if not sorted_matches:
        raise ValueError(
            f"No element in the list matches the given pattern. ({p_data=} - "
            f"{p_item_pattern=}"
        )

    return sorted_matches[0].string
