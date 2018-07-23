# coding: utf-8

import email.utils as eu
import random
import time
from unittest.mock import MagicMock

import pytest

from mozapkpublisher import check_rollout


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

    edit_service_mock = MagicMock()
    new_transaction_mock = MagicMock()
    tracks_mock = MagicMock()
    tracks_get_mock = MagicMock()

    edit_service_mock.insert = lambda body, packageName: new_transaction_mock
    edit_service_mock.tracks = lambda: tracks_mock
    new_transaction_mock.execute = lambda: {'id': random.randint(0, 1000)}
    tracks_mock.get = lambda editId=None, track=None, packageName=None: tracks_get_mock
    tracks_get_mock.execute = tracks

    return edit_service_mock


def test_new_rollout(requests_mock):
    """61.0 is in partial rollout since yesterday, 60.0.1 is at full rollout"""
    def tracks():
        return {'releases': [
                {'name': '61.0',
                 'versionCodes': ['2015506297', '2015506300', '2015565729', '2015565732'],
                 'releaseNotes': [
                    {'language': 'sk', 'text': '* Vylepšenia v rámci Quantum CSS, ktoré urýchľujú načítanie stránok\n* Rýchlejšie posúvanie sa na stránkach'}
                 ],
                 'status': 'inProgress',
                 'userFraction': .1,
                 },
                {'name': '60.0.1',
                 'versionCodes': ['2015558697', '2015558700'],
                 'status': 'completed',
                 }]}
    edit_service_mock = set_up_mocks(requests_mock, tracks)

    with pytest.raises(StopIteration):
        next(check_rollout.check_rollout(edit_service_mock, 'org.mozilla.firefox', 7))

    gen = check_rollout.check_rollout(edit_service_mock, 'org.mozilla.firefox', .5)
    release, age = next(gen)
    assert release['name'] == '61.0'
    assert age >= check_rollout.DAY
    with pytest.raises(StopIteration):
        next(gen)


def test_old_rollout(requests_mock):
    """60.0.2 is in partial rollout for a long time; 60.0.1 is at full rollout"""
    def tracks():
        return {'releases': [
                {'name': '60.0.2',
                 'versionCodes': ['2015562697', '2015562700'],
                 'status': 'inProgress',
                 'userFraction': .99,
                 },
                {'name': '60.0.1',
                 'versionCodes': ['2015558697', '2015558700'],
                 'status': 'completed',
                 }]}
    edit_service_mock = set_up_mocks(requests_mock, tracks)

    gen = check_rollout.check_rollout(edit_service_mock, 'org.mozilla.firefox', 7)
    release, age = next(gen)
    assert release['name'] == '60.0.2'
    assert age >= 10 * check_rollout.DAY
    with pytest.raises(StopIteration):
        next(gen)


def test_rc_rollout(requests_mock):
    """62.0 is not released yet but RC is being rolled out; 61.0 is at full rollout"""
    def tracks():
        return {'releases': [
                {'name': '62.0',
                 'versionCodes': ['2015558697', '2015558700'],
                 'status': 'inProgress',
                 'userFraction': .05,
                 },
                {'name': '61.0',
                 'versionCodes': ['2015506297', '2015506300', '2015565729', '2015565732'],
                 'status': 'completed',
                 }]}
    edit_service_mock = set_up_mocks(requests_mock, tracks)

    with pytest.raises(StopIteration):
        next(check_rollout.check_rollout(edit_service_mock, 'org.mozilla.firefox', 7))
