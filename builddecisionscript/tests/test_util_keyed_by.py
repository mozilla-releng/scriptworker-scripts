import pytest

import build_decision.util.keyed_by as keyed_by


@pytest.mark.parametrize(
    "attributes, target, expected",
    (
        ({"key1": "value1"}, "key1", ["value1"]),
        ({".*y1": "value1"}, "key1", ["value1"]),
        ({"key1": "value1", "default": "default_value"}, "key2", ["default_value"]),
        ({"key1": "value1"}, "nonexistent_key", []),
    ),
)
def test_keymatch(attributes, target, expected):
    """Test keyed-by logic, include regexes."""
    assert keyed_by.keymatch(attributes, target) == expected


@pytest.mark.parametrize(
    "value, item_name, attributes, expected, exception",
    (
        # `value` doesn't match the `by-*` pattern; expect `value` back
        ("not_a_dict", "item_name", {}, "not_a_dict", None),
        (
            {"key1": "value1", "key2": "value2"},
            "item_name",
            {},
            {"key1": "value1", "key2": "value2"},
            False,
        ),
        ({"key1": "value1"}, "item_name", {}, {"key1": "value1"}, None),
        # Directly match a single item
        (
            {
                "by-level": {
                    "1": "level1",
                    "3": "level3",
                }
            },
            "key1",
            {"level": "1"},
            "level1",
            False,
        ),
        # Exception when the only choice is `default`
        (
            {
                "by-level": {
                    "default": "default_level",
                }
            },
            "key1",
            {"level": "1"},
            "level1",
            Exception,
        ),
        # Exception when the attribute doesn't exist or is None and no default value
        (
            {
                "by-level": {
                    "1": "level1",
                    "3": "level3",
                }
            },
            "key1",
            {},
            None,
            Exception,
        ),
        # default value when the attribute doesn't exist or is None
        (
            {
                "by-level": {
                    "1": "level1",
                    "default": "default_level",
                }
            },
            "key1",
            {},
            "default_level",
            False,
        ),
        # Exception on more than 1 match
        (
            {
                "by-level": {
                    ".*1": "level1",
                    ".*21": "level21",
                }
            },
            "key1",
            {"level": "21"},
            None,
            Exception,
        ),
        # Exception on no match
        (
            {
                "by-level": {
                    "1": "level1",
                    "3": "level3",
                }
            },
            "key1",
            {"level": "2"},
            None,
            Exception,
        ),
        # Successful recursive match
        (
            {
                "by-project": {
                    "project1": "project1_level1",
                    "default": {
                        "by-level": {
                            "1": "level1",
                            "default": "default_level",
                        }
                    },
                },
            },
            "key1",
            {},
            "default_level",
            False,
        ),
    ),
)
def test_evaluate_keyed_by(value, item_name, attributes, expected, exception):
    """Add full coverage for evaluate_keyed_by."""
    if exception:
        with pytest.raises(exception):
            keyed_by.evaluate_keyed_by(value, item_name, attributes)
    else:
        assert keyed_by.evaluate_keyed_by(value, item_name, attributes) == expected
