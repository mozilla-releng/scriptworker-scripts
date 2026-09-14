# coding: utf-8

import email.utils as eu
import time
from unittest.mock import create_autospec

import pytest

from mozapkpublisher import check_rollout
from mozapkpublisher.common import store


def set_up_mocks(_requests_mock, tracks):
    now = time.time()
    yesterday = now - check_rollout.DAY
    a_long_time_ago = now - 10 * check_rollout.DAY
    _requests_mock.head('https://archive.mozilla.org/pub/mobile/releases/{}/SHA512SUMS'.format('61.0'),
                        status_code=200, headers={'Last-Modified': eu.formatdate(yesterday, usegmt=True)})
    _requests_mock.head('https://archive.mozilla.org/pub/mobile/releases/{}/SHA512SUMS'.format('60.0.2'),
                        status_code=200, headers={'Last-Modified': eu.formatdate(a_long_time_ago, usegmt=True)})
    _requests_mock.head('https://archive.mozilla.org/pub/mobile/releases/{}/SHA512SUMS'.format('62.0'),
                        status_code=404)

    google_play_mock = create_autospec(store.GooglePlayEdit)
    google_play_mock.get_track_status.return_value = tracks
    return google_play_mock


def test_new_rollout(requests_mock):
    """61.0 is in partial rollout since yesterday, 60.0.1 is at full rollout"""
    tracks = {
        "releases": [{
            "name": "61.0",
            "versionCodes": ["2015506297", "2015506300", "2015565729", "2015565732"],
            "releaseNotes": [
                {
                    "language": "sk",
                    "text": "* Vylepšenia v rámci Quantum CSS, ktoré urýchľujú načítanie stránok\n* Rýchlejšie posúvanie sa na stránkach",
                }
            ],
            "status": "inProgress",
            "userFraction": 0.1,
        }, {
            "name": "60.0.1",
            "versionCodes": ["2015558697", "2015558700"],
            "status": "completed",
        }],
    }

    google_play_mock = set_up_mocks(requests_mock, tracks)

    with pytest.raises(StopIteration):
        next(check_rollout.check_rollout(google_play_mock, 7))

    gen = check_rollout.check_rollout(google_play_mock, .5)
    release, age = next(gen)
    assert release['name'] == '61.0'
    assert age >= check_rollout.DAY
    with pytest.raises(StopIteration):
        next(gen)


def test_old_rollout(requests_mock):
    """60.0.2 is in partial rollout for a long time; 60.0.1 is at full rollout"""
    tracks = {
        "releases": [{
            "name": "60.0.2",
            "versionCodes": ["2015562697", "2015562700"],
            "status": "inProgress",
            "userFraction": 0.99,
        }, {
            "name": "60.0.1",
            "versionCodes": ["2015558697", "2015558700"],
            "status": "completed",
        }],
    }

    google_play_mock = set_up_mocks(requests_mock, tracks)

    gen = check_rollout.check_rollout(google_play_mock, 7)
    release, age = next(gen)
    assert release['name'] == '60.0.2'
    assert age >= 10 * check_rollout.DAY
    with pytest.raises(StopIteration):
        next(gen)


def test_rc_rollout(requests_mock):
    """62.0 is not released yet but RC is being rolled out; 61.0 is at full rollout"""
    tracks = {
        "releases": [{
            "name": "62.0",
            "versionCodes": ["2015558697", "2015558700"],
            "status": "inProgress",
            "userFraction": 0.05,
        }, {
            "name": "61.0",
            "versionCodes": ["2015506297", "2015506300", "2015565729", "2015565732"],
            "status": "completed",
        }],
    }

    google_play_mock = set_up_mocks(requests_mock, tracks)

    with pytest.raises(StopIteration):
        next(check_rollout.check_rollout(google_play_mock, 7))
