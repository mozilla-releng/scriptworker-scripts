import pytest

from mozapkpublisher.common.apk.checker import cross_check_apks, \
    _check_number_of_distinct_packages, _check_correct_apk_product_types, \
    _check_all_apks_have_the_same_package_name, \
    _check_all_apks_have_the_same_version, _check_version_matches_package_name, \
    _check_all_apks_have_the_same_build_id, _check_all_apks_have_the_same_locales, \
    _check_piece_of_metadata_is_unique, _check_apks_version_codes_are_correctly_ordered, \
    _check_all_apks_are_multi_locales, _check_all_architectures_and_api_levels_are_present, \
    _craft_expected_combos, _craft_combos_pretty_names
from mozapkpublisher.common.utils import PRODUCT
from mozapkpublisher.common.exceptions import NotMultiLocaleApk, BadApk, BadSetOfApks


def test_cross_check_apks():
    cross_check_apks({
        'fennec-57.0.multi.android-arm.apk': {
            'api_level': 16,
            'architecture': 'armeabi-v7a',
            'firefox_build_id': '20171112125738',
            'firefox_version': '57.0',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-IN', 'br', 'ca', 'cak', 'cs', 'cy',
                'da', 'de', 'dsb', 'el', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR', 'es-CL', 'es-ES',
                'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd', 'gl', 'gn',
                'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja', 'ka',
                'kab', 'kk', 'kn', 'ko', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my', 'nb-NO',
                'nl', 'nn-NO', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm', 'ro', 'ru', 'sk', 'sl',
                'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'wo', 'xh',
                'zam', 'zh-CN', 'zh-TW',
            ),
            'package_name': 'org.mozilla.firefox',
            'version_code': '2015523297',
        },
        'fennec-57.0.multi.android-i386.apk': {
            'api_level': 16,
            'architecture': 'x86',
            'firefox_build_id': '20171112125738',
            'firefox_version': '57.0',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-IN', 'br', 'ca', 'cak', 'cs', 'cy',
                'da', 'de', 'dsb', 'el', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR', 'es-CL', 'es-ES',
                'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd', 'gl', 'gn',
                'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja', 'ka',
                'kab', 'kk', 'kn', 'ko', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my', 'nb-NO',
                'nl', 'nn-NO', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm', 'ro', 'ru', 'sk', 'sl',
                'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'wo', 'xh',
                'zam', 'zh-CN', 'zh-TW',
            ),
            'package_name': 'org.mozilla.firefox',
            'version_code': '2015523300',
        },
    })
    cross_check_apks({
        'Focus.apk': {
            'api_level': 21,
            'architecture': 'armeabi-v7',
            'package_name': 'org.mozilla.focus',
            'version_code': '11'
        },
        'Klar.apk': {
            'api_level': 21,
            'architecture': 'armeabi-v7',
            'package_name': 'org.mozilla.klar',
            'version_code': '11'
        }
    })


def test_check_number_of_apks():
    _check_number_of_distinct_packages({
        'focus.apk': {
            'package_name': 'org.mozilla.focus'
        },
        'klar-x86.apk': {
            'package_name': 'org.mozilla.klar'
        },
        'klar-arm7.apk': {
            'package_name': 'org.mozilla.klar'
        }
    }, 2)

    with pytest.raises(BadSetOfApks):
        _check_number_of_distinct_packages({
            'focus.apk': {
                'package_name': 'org.mozilla.focus'
            },
            'klar.apk': {
                'package_name': 'org.mozilla.klar'
            },
            'fennec.apk': {
                'package_name': 'org.mozilla.firefox'
            }
        }, 2)


def test_check_correct_apk_product_types():
    _check_correct_apk_product_types({
        'focus.apk': {
            'package_name': 'org.mozilla.focus'
        },
        'klar.apk': {
            'package_name': 'org.mozilla.klar'
        }
    }, [PRODUCT.FOCUS, PRODUCT.KLAR])

    with pytest.raises(BadSetOfApks):
        _check_correct_apk_product_types({
            'fennec.apk': {
                'package_name': 'org.mozilla.firefox'
            },
            'klar.apk': {
                'package_name': 'org.mozilla.klar'
            }
        }, [PRODUCT.FOCUS, PRODUCT.KLAR])


def test_check_all_apks_have_the_same_package_name():
    _check_all_apks_have_the_same_package_name({
        'arm.apk': {
            'package_name': 'org.mozilla.firefox',
        },
        'x86.apk': {
            'package_name': 'org.mozilla.firefox',
        },
    })

    with pytest.raises(BadSetOfApks):
        _check_all_apks_have_the_same_package_name({
            'arm.apk': {
                'package_name': 'org.mozilla.firefox',
            },
            'x86.apk': {
                'package_name': 'org.mozilla.firefox_beta',
            },
        })


def test_check_all_apks_have_the_same_version():
    _check_all_apks_have_the_same_version({
        'arm.apk': {
            'firefox_version': '57.0',
        },
        'x86.apk': {
            'firefox_version': '57.0',
        },
    })

    with pytest.raises(BadSetOfApks):
        _check_all_apks_have_the_same_version({
            'arm.apk': {
                'firefox_version': '57.0',
            },
            'x86.apk': {
                'firefox_version': '57.0.1',
            },
        })


@pytest.mark.parametrize('version, package_name', (
    ('57.0', 'org.mozilla.firefox'),
    ('57.0.1', 'org.mozilla.firefox'),
    ('58.0', 'org.mozilla.firefox_beta'),   # XXX Betas APKs are shipped without "bY"
    ('59.0a1', 'org.mozilla.fennec_aurora'),
))
def test_check_version_matches_package_name(version, package_name):
    _check_version_matches_package_name(version, package_name)


@pytest.mark.parametrize('version, package_name', (
    ('57.0', 'org.mozilla.fennec_aurora'),
    ('57.0.1', 'org.mozilla.firefox_beta'),
    ('57.0.1', 'org.mozilla.fennec_aurora'),
    ('58.0', 'org.mozilla.fennec_aurora'),
    ('59.0a1', 'org.mozilla.firefox'),
    ('59.0a1', 'org.mozilla.firefox_beta'),
))
def test_bad_check_version_matches_package_name(version, package_name):
    with pytest.raises(BadApk):
        _check_version_matches_package_name(version, package_name)


def test_check_all_apks_have_the_same_build_id():
    _check_all_apks_have_the_same_build_id({
        'arm.apk': {
            'firefox_build_id': '20171112125738',
        },
        'x86.apk': {
            'firefox_build_id': '20171112125738',
        },
    })

    with pytest.raises(BadSetOfApks):
        _check_all_apks_have_the_same_build_id({
            'arm.apk': {
                'firefox_build_id': '1',
            },
            'x86.apk': {
                'firefox_build_id': '2',
            },
        })


def test_check_all_apks_have_the_same_locales():
    _check_all_apks_have_the_same_locales({
        'arm.apk': {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        'x86.apk': {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
    })

    with pytest.raises(BadSetOfApks):
        _check_all_apks_have_the_same_locales({
            'arm.apk': {
                'locales': ('en-US', 'es-ES', 'fr'),
            },
            'x86.apk': {
                'locales': ('en-US', 'es-MX', 'fr'),
            },
        })


def test_check_piece_of_metadata_is_unique():
    _check_piece_of_metadata_is_unique('some_key', 'Some Key', {
        'irrelevant_key': {
            'some_key': 'some unique value',
        },
        'another_irrelevant_key': {
            'some_key': 'some unique value',
        },
    })


@pytest.mark.parametrize('apks_metadata_per_paths', ({
    'irrelevant_key': {
        'some_key': 'some value',
    },
    'another_irrelevant_key': {
        'some_key': 'some other value value',
    },
}, {
    # Empty dict to let `all_items` be empty
}))
def test_bad_check_piece_of_metadata_is_unique(apks_metadata_per_paths):
    with pytest.raises(BadSetOfApks):
        _check_piece_of_metadata_is_unique('some_key', 'Some Key', apks_metadata_per_paths)


def test_check_apks_version_codes_are_correctly_ordered():
    _check_apks_version_codes_are_correctly_ordered({
        'arm.apk': {
            'version_code': '0',
            'architecture': 'armeabi-v7a',
        },
        'x86.apk': {
            'version_code': '1',
            'architecture': 'x86',
        },
    })


@pytest.mark.parametrize('apks_metadata_per_paths', ({
    'arm.apk': {
        'version_code': '1',
        'architecture': 'armeabi-v7a',
    },
    'x86.apk': {
        'version_code': '1',
        'architecture': 'x86',
    },
}, {
    'arm.apk': {
        'version_code': '1',
        'architecture': 'armeabi-v7a',
    },
    'x86.apk': {
        'version_code': '0',
        'architecture': 'x86',
    },
}))
def test_bad_check_apks_version_codes_are_correctly_ordered(apks_metadata_per_paths):
    with pytest.raises(BadSetOfApks):
        _check_apks_version_codes_are_correctly_ordered(apks_metadata_per_paths)


def test_check_all_apks_are_multi_locales():
    _check_all_apks_are_multi_locales({
        'arm.apk': {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        'x86.apk': {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
    })


@pytest.mark.parametrize('apks_metadata_per_paths, expected_exception', ((
    {
        'arm.apk': {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        'x86.apk': {
            'locales': ('en-US',),
        },
    },
    NotMultiLocaleApk,
), (
    {
        'arm.apk': {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        'x86.apk': {
            'locales': (),
        },
    },
    NotMultiLocaleApk,
), (
    {
        'arm.apk': {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        'x86.apk': {
            'locales': 'en-US',
        },
    },
    BadApk,
)))
def test_bad_check_all_apks_are_multi_locales(apks_metadata_per_paths, expected_exception):
    with pytest.raises(expected_exception):
        _check_all_apks_are_multi_locales(apks_metadata_per_paths)


def test_check_all_architectures_and_api_levels_are_present():
    _check_all_architectures_and_api_levels_are_present({
        'arm.apk': {
            'firefox_version': '57.0',
            'architecture': 'armeabi-v7a',
            'api_level': 16,
        },
        'x86.apk': {
            'firefox_version': '57.0',
            'architecture': 'x86',
            'api_level': 16,
        },
    })


@pytest.mark.parametrize('apks_metadata_per_paths', ({
    'arm.apk': {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
    },
    'lying-x86.apk': {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
    },
}, {
    'unsupported-api-level-arm.apk': {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 15,
    },
    'x86.apk': {
        'firefox_version': '57.0',
        'architecture': 'x86',
        'api_level': 16,
    },
}, {
    'arm.apk': {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
    },
    'unsupported-api-level-arm.apk': {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 15,
    },
    'x86.apk': {
        'firefox_version': '57.0',
        'architecture': 'x86',
        'api_level': 16,
    },
}))
def test_bad_check_all_architectures_and_api_levels_are_present(apks_metadata_per_paths):
    with pytest.raises(BadSetOfApks):
        _check_all_architectures_and_api_levels_are_present(apks_metadata_per_paths)


@pytest.mark.parametrize('firefox_version, expected_api_levels, expected_architectures, expected', (
    ('55.0', (15,), ('armeabi-v7a', 'x86'), set((('armeabi-v7a', 15), ('x86', 15)))),
    ('57.0', (16,), ('armeabi-v7a', 'x86'), set((('armeabi-v7a', 16), ('x86', 16)))),
))
def test_craft_expected_combos(firefox_version, expected_api_levels, expected_architectures, expected):
    assert _craft_expected_combos(firefox_version, expected_api_levels, expected_architectures) == expected


def test_craft_combos_pretty_names():
    assert _craft_combos_pretty_names((('x86', 15), ('armeabi-v7a', 15))) == 'x86 API 15+, armeabi-v7a API 15+'
