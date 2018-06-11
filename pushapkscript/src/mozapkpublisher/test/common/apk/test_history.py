import pytest

from mozapkpublisher.common.apk.history import get_expected_api_levels_for_version, \
    get_expected_architectures_for_version, _get_expected_things_for_version, \
    _is_firefox_version_in_range, get_firefox_major_version_number


@pytest.mark.parametrize('firefox_version, expected', (
    ('32.0b9', (9,)),
    ('37.0a2', (9, 11)),
    ('45.0', (9, 11,)),
    ('47.0.1', (9, 15,)),
    ('49.0', (15,)),
    ('55.0.2', (15,)),
    ('57.0', (16,)),
))
def test_get_expected_api_levels_for_version(firefox_version, expected):
    assert get_expected_api_levels_for_version(firefox_version) == expected


@pytest.mark.parametrize('firefox_version, expected', (
    ('4.0', ('armeabi-v7a',)),
    ('14.0', ('armeabi-v7a', 'x86')),
))
def test_get_expected_architectures_for_version(firefox_version, expected):
    assert get_expected_architectures_for_version(firefox_version) == expected


def test_get_expected_things_for_version():
    dict_of_things = {
        'an_old_thing': {
            'first_firefox_version': 1,
            'last_firefox_version': 2,
        },
        'a_current_thing': {
            'first_firefox_version': 3,
        },
        'zzz-another_current_thing': {
            'first_firefox_version': 4,
            'last_firefox_version': 999,
        },
        'a_future_thing': {
            'first_firefox_version': 1000,
        },
    }
    assert _get_expected_things_for_version('57.0', dict_of_things, 'name') == (
        'a_current_thing', 'zzz-another_current_thing'
    )


@pytest.mark.parametrize('firefox_version, range_dict, expected', (
    ('55.0', {'first_firefox_version': 56}, False),
    ('56.0', {'first_firefox_version': 56}, True),
    ('57.0.1', {'first_firefox_version': 56}, True),

    ('45.0.2', {'first_firefox_version': 46, 'last_firefox_version': 55}, False),
    ('46.0', {'first_firefox_version': 46, 'last_firefox_version': 55}, True),
    ('46.0.1', {'first_firefox_version': 46, 'last_firefox_version': 55}, True),
    ('55.0', {'first_firefox_version': 46, 'last_firefox_version': 55}, True),
    ('55.0.2', {'first_firefox_version': 46, 'last_firefox_version': 55}, True),
    ('56.0.2', {'first_firefox_version': 46, 'last_firefox_version': 55}, False),
))
def test_is_firefox_version_in_range(firefox_version, range_dict, expected):
    assert _is_firefox_version_in_range(firefox_version, range_dict) == expected


@pytest.mark.parametrize('firefox_version, expected', (
    ('59.0a1', 59),
    ('58.0b1', 58),
    ('57.0', 57),
    ('57.0.1', 57),
))
def test_get_firefox_major_version_number(firefox_version, expected):
    assert get_firefox_major_version_number(firefox_version) == expected
