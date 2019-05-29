import pytest

from mozapkpublisher.common.apk.history import (
    craft_combos_pretty_names,
    get_expected_combos,
    get_firefox_major_version_number,
    _is_firefox_version_in_range,
)


@pytest.mark.parametrize('firefox_version, package_name, expected', ((
    '32.0b9',
    'org.mozilla.firefox_beta',
    set([('x86', 9), ('armeabi-v7a', 9)]),
), (
    '37.0a2',
    'org.mozilla.fennec_aurora',
    set([('x86', 11), ('armeabi-v7a', 9), ('armeabi-v7a', 11)]),
), (
    '45.0',
    'org.mozilla.firefox',
    set([('x86', 11), ('armeabi-v7a', 9), ('armeabi-v7a', 11)]),
), (
    '47.0.1',
    'org.mozilla.firefox',
    set([('x86', 15), ('armeabi-v7a', 9), ('armeabi-v7a', 15)]),
), (
    '49',
    'org.mozilla.firefox',
    set([('x86', 15), ('armeabi-v7a', 15)]),
), (
    '55.0.2',
    'org.mozilla.firefox',
    set([('x86', 15), ('armeabi-v7a', 15)]),
), (
    '57.0',
    'org.mozilla.firefox',
    set([('x86', 16), ('armeabi-v7a', 16)]),
), (
    '66.0a1',
    'org.mozilla.fennec_aurora',
    set([('x86', 16), ('armeabi-v7a', 16), ('arm64-v8a', 21)]),
), (
    '67.0a1',
    'org.mozilla.fennec_aurora',
    set([('x86', 16), ('x86_64', 21), ('armeabi-v7a', 16), ('arm64-v8a', 21)]),
), (
    '68.0a1',
    'org.mozilla.fennec_aurora',
    set([('x86', 16), ('x86_64', 21), ('armeabi-v7a', 16), ('arm64-v8a', 21)]),
), (
    '66.0b1',
    'org.mozilla.firefox_beta',
    set([('x86', 16), ('armeabi-v7a', 16)]),
), (
    '67.0b1',
    'org.mozilla.firefox_beta',
    set([('x86', 16), ('x86_64', 21), ('armeabi-v7a', 16), ('arm64-v8a', 21)]),
), (
    '68.0b1',
    'org.mozilla.firefox_beta',
    set([('x86', 16), ('x86_64', 21), ('armeabi-v7a', 16), ('arm64-v8a', 21)]),
), (
    '66.0',
    'org.mozilla.firefox',
    set([('x86', 16), ('armeabi-v7a', 16)]),
), (
    '67.0',
    'org.mozilla.firefox',
    set([('x86', 16), ('x86_64', 21), ('armeabi-v7a', 16)]),
), (
    '68.0',
    'org.mozilla.firefox',
    set([('x86', 16), ('x86_64', 21), ('armeabi-v7a', 16), ('arm64-v8a', 21)]),
)))
def test_get_expected_combos(firefox_version, package_name, expected):
    assert get_expected_combos(firefox_version, package_name) == expected


def test_empty_get_expected_combos():
    with pytest.raises(ValueError):
        get_expected_combos('8.0', 'some.package.name')


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


def test_craft_combos_pretty_names():
    assert craft_combos_pretty_names((('x86', 15), ('armeabi-v7a', 15))) == 'x86 API 15+, armeabi-v7a API 15+'
