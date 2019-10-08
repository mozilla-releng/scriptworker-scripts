import pytest

from pushapkscript.utils import filter_out_identical_values


@pytest.mark.parametrize('list_, expected', (
    (['foo'], ['foo']),
    (['foo', 'bar'], ['bar', 'foo']),
    (['foo', 'bar', 'foo'], ['bar', 'foo']),
    (['foo', 'foo', 'bar'], ['bar', 'foo']),
    (['foo', 'foo', 'bar', 'bar'], ['bar', 'foo']),
    ([1, 2, 1, 1, 1], [1, 2]),
))
def test_filter_out_identical_values(list_, expected):
    assert sorted(filter_out_identical_values(list_)) == expected
