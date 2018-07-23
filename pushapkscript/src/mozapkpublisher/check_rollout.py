#!/usr/bin/env python3

import argparse
import calendar
import email.utils as eu
import logging
import time

import requests

from mozapkpublisher.common import googleplay

DAY = 24 * 60 * 60

logger = logging.getLogger(__name__)


def check_rollout(edits_service, package_name, days):
    """Check if package_name has a release on staged rollout for too long"""
    edit = edits_service.insert(body={}, packageName=package_name).execute()
    response = edits_service.tracks().get(editId=edit['id'], track='production', packageName=package_name).execute()
    releases = response['releases']
    for release in releases:
        if release['status'] == 'inProgress':
            url = 'https://archive.mozilla.org/pub/mobile/releases/{}/SHA512SUMS'.format(release['name'])
            resp = requests.head(url)
            if resp.status_code != 200:
                if resp.status_code != 404:  # 404 is expected for release candidates
                    logger.warning("Could not check %s: %s", url, resp.status_code)
                continue
            age = time.time() - calendar.timegm(eu.parsedate(resp.headers['Last-Modified']))
            if age >= days * DAY:
                yield release, age


def main():
    parser = argparse.ArgumentParser(description='Check for in-progress Firefox for Android staged rollout')
    parser.add_argument('service_account', help='The service account email')
    parser.add_argument('credentials', help='The p12 authentication file', type=argparse.FileType(mode='rb'))
    parser.add_argument('--days', help='The time before we warn about incomplete staged rollout of a release (default: 7)',
                        type=int, default=7)
    config = parser.parse_args()

    # TODO: use googleplay.EditService when that is ported to v3
    service = googleplay.connect(config.service_account, config.credentials.name, 'v3').edits()
    for (release, age) in check_rollout(service, 'org.mozilla.firefox', config.days):
        print('fennec {} is on staged rollout at {}% but it shipped {} days ago'.format(
              release['name'], int(release['userFraction'] * 100), int(age / DAY)))


if __name__ == '__main__':
    main()
