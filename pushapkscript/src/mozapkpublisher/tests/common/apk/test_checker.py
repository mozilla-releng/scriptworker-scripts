from mock import Mock
import pytest

from mozapkpublisher.common.apk.checker import (
    cross_check_apks,
    _check_all_apks_have_the_same_firefox_version,
    _check_version_matches_package_name,
    _check_all_apks_have_the_same_build_id,
    _check_all_apks_have_the_same_locales,
    _check_piece_of_metadata_is_unique,
    _check_apks_version_codes_are_correctly_ordered,
    _check_all_apks_are_multi_locales,
    _check_all_architectures_and_api_levels_are_present,
    _check_package_names)
from mozapkpublisher.common.exceptions import NotMultiLocaleApk, BadApk, BadSetOfApks


def mock_apk(filename):
    apk = Mock()
    apk.name = filename
    return apk


@pytest.mark.parametrize('apks_metadata_per_paths, product_types, should_fail', (({
    mock_apk('fenix.apk'): {
        'package_name': 'org.mozilla.fenix'
    },
    mock_apk('focus.apk'): {
        'package_name': 'org.mozilla.focus'
    },
    mock_apk('klar.apk'): {
        'package_name': 'org.mozilla.klar'
    },
    mock_apk('reference-browser.apk'): {
        'package_name': 'org.mozilla.reference.browser'
    }
}, ['org.mozilla.fenix', 'org.mozilla.focus', 'org.mozilla.klar', 'org.mozilla.reference.browser'], False), ({
    mock_apk('fennec.apk'): {
        'package_name': 'org.mozilla.firefox'
    },
    mock_apk('klar.apk'): {
        'package_name': 'org.mozilla.klar'
    },
    mock_apk('reference-browser.apk'): {
        'package_name': 'org.mozilla.reference.browser'
    }
}, ['org.mozilla.focus', 'org.mozilla.klar'], True), ({
    mock_apk('fennec.apk'): {
        'package_name': 'org.mozilla.firefox'
    },
    mock_apk('klar-x86.apk'): {
        'package_name': 'org.mozilla.klar'
    },
    mock_apk('klar-arm.apk'): {
        'package_name': 'org.mozilla.klar'
    }
}, ['org.mozilla.focus', 'org.mozilla.klar', 'org.mozilla.reference.browser'], True)))
def test_check_correct_apk_package_names(apks_metadata_per_paths, product_types, should_fail):
    if should_fail:
        with pytest.raises(BadSetOfApks):
            _check_package_names(product_types, apks_metadata_per_paths)
    else:
        _check_package_names(product_types, apks_metadata_per_paths)


@pytest.mark.parametrize('apks_metadata_per_paths, package_names_check, skip_checks_fennec, skip_check_multiple_locales, skip_check_same_locales, skip_check_ordered_version_codes', ((   # noqa
    {
        mock_apk('fennec-57.0.multi.android-arm.apk'): {
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
        mock_apk('fennec-57.0.multi.android-i386.apk'): {
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
    },
    ['org.mozilla.firefox'],
    False,
    False,
    False,
    False,
), (
    {
        mock_apk('/builds/scriptworker/work/cot/KfG055G3RTCt1etlbYlzkg/public/build/target.apk'): {
            'api_level': 16,
            'architecture': 'armeabi-v7a',
            'firefox_version': '66.0a1',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.fennec_aurora',
            'version_code': '2015605649',
        },
        mock_apk('/builds/scriptworker/work/cot/T26ZMbPPRJqCBfqTEfbHyg/public/build/target.apk'): {
            'api_level': 16,
            'architecture': 'x86',
            'firefox_version': '66.0a1',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.fennec_aurora',
            'version_code': '2015605653',
        },
        mock_apk('/builds/scriptworker/work/cot/dl5vhYhGRpG7MEj0ODyFuQ/public/build/target.apk'): {
            'api_level': 21,
            'architecture': 'arm64-v8a',
            'firefox_version': '66.0a1',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.fennec_aurora',
            'version_code': '2015605651',
        },
    },
    ['org.mozilla.fennec_aurora'],
    False,
    False,
    False,
    False,
), (
    {
        mock_apk('/builds/scriptworker/work/cot/KfG055G3RTCt1etlbYlzkg/public/build/target.apk'): {
            'api_level': 16,
            'architecture': 'armeabi-v7a',
            'firefox_version': '67.0a1',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.fennec_aurora',
            'version_code': '2015605649',
        },
        mock_apk('/builds/scriptworker/work/cot/T26ZMbPPRJqCBfqTEfbHyg/public/build/target.apk'): {
            'api_level': 16,
            'architecture': 'x86',
            'firefox_version': '67.0a1',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.fennec_aurora',
            'version_code': '2015605653',
        },
        mock_apk('/builds/scriptworker/work/cot/dl5vhYhGRpG7MEj0ODyFuQ/public/build/target.apk'): {
            'api_level': 21,
            'architecture': 'arm64-v8a',
            'firefox_version': '67.0a1',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.fennec_aurora',
            'version_code': '2015605651',
        },
        mock_apk('/builds/scriptworker/work/cot/somtaskId/public/build/target.apk'): {
            'api_level': 21,
            'architecture': 'x86_64',
            'firefox_version': '67.0a1',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.fennec_aurora',
            'version_code': '2015605655',
        },
    },
    ['org.mozilla.fennec_aurora'],
    False,
    False,
    False,
    False,
), (
    {
        mock_apk('/some/beta/target.arm.apk'): {
            'api_level': 16,
            'architecture': 'armeabi-v7a',
            'firefox_version': '67.0',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.firefox_beta',
            'version_code': '1',
        },
        mock_apk('/some/beta/target.x86.apk'): {
            'api_level': 16,
            'architecture': 'x86',
            'firefox_version': '67.0',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.firefox_beta',
            'version_code': '3',
        },
        mock_apk('/some/beta/target.aarch64.apk'): {
            'api_level': 21,
            'architecture': 'arm64-v8a',
            'firefox_version': '67.0',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.firefox_beta',
            'version_code': '2015605651',
        },
        mock_apk('/some/beta/target.x86_64.apk'): {
            'api_level': 21,
            'architecture': 'x86_64',
            'firefox_version': '67.0',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.firefox_beta',
            'version_code': '4',
        },
    },
    ['org.mozilla.firefox_beta'],
    False,
    False,
    False,
    False,
), (
    {
        mock_apk('/some/release/target.arm.apk'): {
            'api_level': 16,
            'architecture': 'armeabi-v7a',
            'firefox_version': '68.0',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.firefox',
            'version_code': '1',
        },
        mock_apk('/some/release/target.x86.apk'): {
            'api_level': 16,
            'architecture': 'x86',
            'firefox_version': '68.0',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.firefox',
            'version_code': '3',
        },
        mock_apk('/some/release/target.aarch64.apk'): {
            'api_level': 21,
            'architecture': 'arm64-v8a',
            'firefox_version': '68.0',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.firefox',
            'version_code': '2015605651',
        },
        mock_apk('/some/release/target.x86_64.apk'): {
            'api_level': 21,
            'architecture': 'x86_64',
            'firefox_version': '68.0',
            'firefox_build_id': '20190115103851',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cak',
                'cs', 'cy', 'da', 'de', 'dsb', 'el', 'en-CA', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR',
                'es-CL', 'es-ES', 'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd',
                'gl', 'gn', 'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja',
                'ka', 'kab', 'kk', 'kn', 'ko', 'lij', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my',
                'nb-NO', 'ne-NP', 'nl', 'nn-NO', 'oc', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm',
                'ro', 'ru', 'sk', 'sl', 'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'trs',
                'uk', 'ur', 'uz', 'vi', 'wo', 'xh', 'zam', 'zh-CN', 'zh-TW'
            ),
            'package_name': 'org.mozilla.firefox',
            'version_code': '4',
        },
    },
    ['org.mozilla.firefox'],
    False,
    False,
    False,
    False,
), (
    {
        mock_apk('Focus.apk'): {
            'api_level': 21,
            'architecture': 'armeabi-v7',
            'package_name': 'org.mozilla.focus',
            'version_code': '11'
        },
        mock_apk('Klar.apk'): {
            'api_level': 21,
            'architecture': 'armeabi-v7',
            'package_name': 'org.mozilla.klar',
            'version_code': '11'
        }
    },
    ['org.mozilla.focus', 'org.mozilla.klar'],
    True,
    True,
    True,
    True,
)))
def test_cross_check_apks(apks_metadata_per_paths, package_names_check, skip_checks_fennec, skip_check_multiple_locales,
                          skip_check_same_locales, skip_check_ordered_version_codes):
    cross_check_apks(apks_metadata_per_paths, package_names_check, skip_checks_fennec, skip_check_multiple_locales,
                     skip_check_same_locales, skip_check_ordered_version_codes)


def test_check_all_apks_have_the_same_firefox_version():
    _check_all_apks_have_the_same_firefox_version({
        mock_apk('arm.apk'): {
            'firefox_version': '57.0',
        },
        mock_apk('x86.apk'): {
            'firefox_version': '57.0',
        },
    })

    with pytest.raises(BadSetOfApks):
        _check_all_apks_have_the_same_firefox_version({
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
    # XXX 68 allows 68.Y numbers
    ('68.0', 'org.mozilla.firefox_beta'),
    ('68.1', 'org.mozilla.firefox_beta'),
    ('68.2', 'org.mozilla.firefox_beta'),
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
        mock_apk('arm.apk'): {
            'firefox_build_id': '20171112125738',
        },
        mock_apk('x86.apk'): {
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
        mock_apk('arm.apk'): {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        mock_apk('x86.apk'): {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
    })

    with pytest.raises(BadSetOfApks):
        _check_all_apks_have_the_same_locales({
            mock_apk('arm.apk'): {
                'locales': ('en-US', 'es-ES', 'fr'),
            },
            mock_apk('x86.apk'): {
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


@pytest.mark.parametrize('apks_metadata_per_paths', ({
    mock_apk('arm.apk'): {
        'version_code': '0',
        'architecture': 'armeabi-v7a',
    },
    mock_apk('x86.apk'): {
        'version_code': '1',
        'architecture': 'x86',
    },
}, {
    mock_apk('arm.apk'): {
        'version_code': '0',
        'architecture': 'armeabi-v7a',
    },
    mock_apk('arm64.apk'): {
        'version_code': '1',
        'architecture': 'arm64-v8a',
    },
    mock_apk('x86.apk'): {
        'version_code': '2',
        'architecture': 'x86',
    },
}, {
    mock_apk('arm.apk'): {
        'version_code': '0',
        'architecture': 'armeabi-v7a',
    },
    mock_apk('arm64.apk'): {
        'version_code': '1',
        'architecture': 'arm64-v8a',
    },
    mock_apk('x86.apk'): {
        'version_code': '2',
        'architecture': 'x86',
    },
    mock_apk('x86_64.apk'): {
        'version_code': '3',
        'architecture': 'x86_64',
    },
}))
def test_check_apks_version_codes_are_correctly_ordered(apks_metadata_per_paths):
    _check_apks_version_codes_are_correctly_ordered(apks_metadata_per_paths)


@pytest.mark.parametrize('apks_metadata_per_paths', ({
    mock_apk('arm.apk'): {
        'version_code': '1',
        'architecture': 'armeabi-v7a',
    },
    mock_apk('x86.apk'): {
        'version_code': '1',
        'architecture': 'x86',
    },
}, {
    mock_apk('x86.apk'): {
        'version_code': '0',
        'architecture': 'x86',
    },
    mock_apk('arm.apk'): {
        'version_code': '1',
        'architecture': 'armeabi-v7a',
    },
}, {
    mock_apk('x86.apk'): {
        'version_code': '0',
        'architecture': 'x86',
    },
    mock_apk('arm64.apk'): {
        'version_code': '1',
        'architecture': 'arm64-v8a',
    },
}, {
    mock_apk('arm64.apk'): {
        'version_code': '1',
        'architecture': 'arm64-v8a',
    },
    mock_apk('arm.apk'): {
        'version_code': '2',
        'architecture': 'armeabi-v7a',
    },
}, {
    mock_apk('x86_64.apk'): {
        'version_code': '1',
        'architecture': 'x86_64',
    },
    mock_apk('x86.apk'): {
        'version_code': '2',
        'architecture': 'x86',
    },
}, {
    mock_apk('x86_64.apk'): {
        'version_code': '1',
        'architecture': 'x86_64',
    },
    mock_apk('arm64.apk'): {
        'version_code': '2',
        'architecture': 'arm64-v8a',
    },
}))
def test_bad_check_apks_version_codes_are_correctly_ordered(apks_metadata_per_paths):
    with pytest.raises(BadSetOfApks):
        _check_apks_version_codes_are_correctly_ordered(apks_metadata_per_paths)


def test_check_all_apks_are_multi_locales():
    _check_all_apks_are_multi_locales({
        mock_apk('arm.apk'): {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        mock_apk('x86.apk'): {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
    })


@pytest.mark.parametrize('apks_metadata_per_paths, expected_exception', ((
    {
        mock_apk('arm.apk'): {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        mock_apk('x86.apk'): {
            'locales': ('en-US',),
        },
    },
    NotMultiLocaleApk,
), (
    {
        mock_apk('arm.apk'): {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        mock_apk('x86.apk'): {
            'locales': (),
        },
    },
    NotMultiLocaleApk,
), (
    {
        mock_apk('arm.apk'): {
            'locales': ('en-US', 'es-ES', 'fr'),
        },
        mock_apk('x86.apk'): {
            'locales': 'en-US',
        },
    },
    BadApk,
)))
def test_bad_check_all_apks_are_multi_locales(apks_metadata_per_paths, expected_exception):
    with pytest.raises(expected_exception):
        _check_all_apks_are_multi_locales(apks_metadata_per_paths)


@pytest.mark.parametrize('apks_metadata_per_paths', ({
    mock_apk('arm.apk'): {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox'
    },
    mock_apk('x86.apk'): {
        'firefox_version': '57.0',
        'architecture': 'x86',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox'
    },
}, {
    mock_apk('arm.apk'): {
        'firefox_version': '66.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox'
    },
    mock_apk('x86.apk'): {
        'firefox_version': '66.0',
        'architecture': 'x86',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox'
    },
}, {
    mock_apk('arm.apk'): {
        'firefox_version': '66.0a1',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
        'package_name': 'org.mozilla.fennec_aurora'
    },
    mock_apk('x86.apk'): {
        'firefox_version': '66.0a1',
        'architecture': 'x86',
        'api_level': 16,
        'package_name': 'org.mozilla.fennec_aurora'
    },
    mock_apk('aarch64.apk'): {
        'firefox_version': '66.0a1',
        'architecture': 'arm64-v8a',
        'api_level': 21,
        'package_name': 'org.mozilla.fennec_aurora'
    },
}))
def test_check_all_architectures_and_api_levels_are_present(apks_metadata_per_paths):
    _check_all_architectures_and_api_levels_are_present(apks_metadata_per_paths)


@pytest.mark.parametrize('apks_metadata_per_paths', ({
    mock_apk('arm.apk'): {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox',
    },
    mock_apk('lying-x86.apk'): {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox',
    },
}, {
    mock_apk('unsupported-api-level-arm.apk'): {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 15,
        'package_name': 'org.mozilla.firefox',
    },
    mock_apk('x86.apk'): {
        'firefox_version': '57.0',
        'architecture': 'x86',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox',
    },
}, {
    mock_apk('arm.apk'): {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox',
    },
    mock_apk('unsupported-api-level-arm.apk'): {
        'firefox_version': '57.0',
        'architecture': 'armeabi-v7a',
        'api_level': 15,
        'package_name': 'org.mozilla.firefox',
    },
    mock_apk('x86.apk'): {
        'firefox_version': '57.0',
        'architecture': 'x86',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox',
    },
}, {
    mock_apk('arm.apk'): {
        'firefox_version': '66.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox_beta'
    },
    mock_apk('x86.apk'): {
        'firefox_version': '66.0',
        'architecture': 'x86',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox_beta'
    },
    mock_apk('aarch64.apk'): {
        'firefox_version': '66.0',
        'architecture': 'arm64-v8a',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox_beta'
    },
}, {
    mock_apk('arm.apk'): {
        'firefox_version': '66.0',
        'architecture': 'armeabi-v7a',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox'
    },
    mock_apk('x86.apk'): {
        'firefox_version': '66.0',
        'architecture': 'x86',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox'
    },
    mock_apk('aarch64.apk'): {
        'firefox_version': '66.0',
        'architecture': 'arm64-v8a',
        'api_level': 16,
        'package_name': 'org.mozilla.firefox'
    },
}))
def test_bad_check_all_architectures_and_api_levels_are_present(apks_metadata_per_paths):
    with pytest.raises(BadSetOfApks):
        _check_all_architectures_and_api_levels_are_present(apks_metadata_per_paths)
