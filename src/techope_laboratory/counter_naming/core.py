"""Define tools that facilitate the sorting of elements by counter."""

import encodings.utf_8
import re
from collections.abc import Callable, Iterable, Iterator
from typing import Final, cast

DEFAULT_COUNTER_KEY_PATTERN: Final[str] = "counter"


def get_default_counter_pattern(
    p_pattern_key: str = DEFAULT_COUNTER_KEY_PATTERN,
) -> re.Pattern[str]:
    """
    Retrieve the default pattern for a counter, using the provided key pattern.

    Example :
        - "3"
        - "489"
        - "4569.54"
        - "5.6"
        - "14964.186.4786.5.4186"

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
    Convert a counter to a tuple of int.

    :param p_counter: The counter to convert.
    :return: Tuple of int representing the counter.
    :raises ValueError: If any part between dots is not a valid integer.
    """
    l_counter: str = (
        p_counter
        if isinstance(p_counter, str) else
        p_counter.decode(
            encoding=encodings.utf_8.getregentry().name,
        )
    )

    returned_value: tuple[int, ...]
    if l_counter:
        l_counter_parts: list[str] = l_counter.split(
            sep=".",
        )
        try:
            returned_value = tuple(
                int(l_part)
                for l_part in l_counter_parts
            )
        except ValueError as l_value_error:
            l_counter_to_display: str = (
                f'"{p_counter}"'
                if isinstance(p_counter, str) else
                str(p_counter)
            )
            raise ValueError(
                f"Invalid counter: {l_counter_to_display}. All counter parts "
                "(between dots) must be valid integers.",
            ) from l_value_error

    else:
        returned_value = ()

    return returned_value


def sort_by_counter[T: (str, bytes)](
    p_data: Iterable[T],
    p_item_pattern: re.Pattern[T],
    p_counter_key_pattern: str = DEFAULT_COUNTER_KEY_PATTERN,
    p_func_counter_to_ints: Callable[[T], tuple[int, ...]] = (
        default_counter_to_ints
    ),
    p_reverse: bool = False,
) -> list[re.Match[T]]:
    """
    Sort a collection of data based on the counter associated with each item.

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
    :param p_func_counter_to_ints: A function transforming the extracted counter
     (from the named group <p_counter_key_pattern>) into a tuple of integers
     used for sorting.
    :param p_reverse: Indicates whether the sort order should be reversed.
    :return: A list of re.Match objects from <p_data> sorted by counter.
    :raises RuntimeError: If <p_item_pattern> does not define the named group
     <p_counter_key_pattern>.
    """
    if p_counter_key_pattern not in p_item_pattern.groupindex:
        raise RuntimeError(
            f"The given pattern {p_item_pattern} must define a mandatory named "
            f'group "{p_counter_key_pattern}"',
        )

    # 1 - Apply the `<p_item_pattern>` to each item in `<p_data>`.
    # 2 - Filter out items that do not match the pattern.
    l_matches: list[re.Match[T]] = [
        l_match
        for l_item in p_data
        if (l_match := p_item_pattern.fullmatch(
            string=l_item,
        )) is not None
    ]

    # 5 - Sort the matching items based on this tuple of integers.
    return sorted(
        l_matches,
        # 4 - Convert the string value from the named group into a tuple of
        #     integers for each matching item.
        key=lambda l_match: p_func_counter_to_ints(
            # 3 - Retrieve the named group defined by `<p_counter_key_pattern>`
            #     for each item that matches the pattern.
            cast(
                typ=T,
                val=l_match[p_counter_key_pattern],
            ),
        ),
        reverse=p_reverse,
    )


def get_max_counter_element[T: (str, bytes)](
    p_data: Iterable[T],
    p_item_pattern: re.Pattern[T],
    p_counter_key_pattern: str = DEFAULT_COUNTER_KEY_PATTERN,
    p_func_counter_to_ints: Callable[[T], tuple[int, ...]] = (
        default_counter_to_ints
    ),
) -> T:
    """
    Retrieve the element with the highest counter.

    :param p_data: The collection of data entries containing a counter.
    :param p_item_pattern: The regular expression pattern that must be matched
     by the elements in <p_data> to be considered. This pattern must define a
     named group <p_counter_key_pattern>.
    :param p_counter_key_pattern: The name of the group to be extracted from
     the regular expression <p_item_pattern>.
    :param p_func_counter_to_ints: A function transforming the extracted counter
     (from the named group <p_counter_key_pattern>) into a tuple of integers
     used for sorting.
    :return: The element with the highest counter in <p_data>.
    :raises RuntimeError: If <p_item_pattern> does not define the named group
     <p_counter_key_pattern>.
    :raises ValueError: If no elements in <p_data> match the pattern
     <p_item_pattern>.
    """
    if p_counter_key_pattern not in p_item_pattern.groupindex:
        raise RuntimeError(
            f"The given pattern {p_item_pattern} must define a mandatory named "
            f'group "{p_counter_key_pattern}"',
        )

    l_matches: Iterator[re.Match[T]] = (
        l_match
        for l_item in p_data
        if (l_match := p_item_pattern.fullmatch(
            string=l_item,
        )) is not None
    )

    try:
        l_max_match: re.Match[T] = max(
            l_matches,
            key=lambda l_match: p_func_counter_to_ints(
                cast(
                    typ=T,
                    val=l_match[p_counter_key_pattern],
                ),
            ),
        )
    except ValueError as l_value_error:
        raise ValueError(
            f"No element in the list matches the given pattern. ({p_data=} - "
            f"{p_item_pattern=})"
        ) from l_value_error

    return l_max_match.string


def get_new_counter[T: (str, bytes)](
    p_data: Iterable[T],
    p_item_pattern: re.Pattern[T],
    p_counter_key_pattern: str = DEFAULT_COUNTER_KEY_PATTERN,
    p_func_counter_to_ints: Callable[[T], tuple[int, ...]] = (
        default_counter_to_ints
    ),
) -> tuple[int, ...]:
    """
    Determine the numbers for a counter of a new element.

    :param p_data: The collection of data entries containing a counter.
    :param p_item_pattern: The regular expression pattern that must be matched
     by the elements in <p_data> to be considered. This pattern must define a
     named group specified by <p_counter_key_pattern>.
    :param p_counter_key_pattern: The name of the group to be extracted from
     the regular expression <p_item_pattern>.
    :param p_func_counter_to_ints: A function transforming the extracted counter
     (from the named group <p_counter_key_pattern>) into a tuple of integers
     used for sorting.
    :return: A tuple representing the next counter value to be used.
    """
    l_returned_value: tuple[int, ...]
    try:
        l_max_counter_element: T = get_max_counter_element(
            p_data=p_data,
            p_item_pattern=p_item_pattern,
            p_counter_key_pattern=p_counter_key_pattern,
            p_func_counter_to_ints=p_func_counter_to_ints,
        )
    except ValueError:
        l_returned_value = (1,)
    else:
        l_match = p_item_pattern.fullmatch(
            string=l_max_counter_element,
        )

        if l_match:
            l_max_tuple: tuple[int, ...] = p_func_counter_to_ints(
                cast(
                    typ=T,
                    val=l_match[p_counter_key_pattern],
                ),
            )

            if l_max_tuple:
                l_returned_value = (*l_max_tuple[:-1], l_max_tuple[-1] + 1)
            else:
                l_returned_value = (1,)
        else:
            l_returned_value = (1,)

    return l_returned_value
