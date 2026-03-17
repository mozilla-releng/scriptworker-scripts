#!/usr/bin/env python
"""Tests for iOS version manipulation (xcconfig files)."""

import pytest
from mozilla_version.ios import MobileIosVersion

import treescript.github.versionmanip as vmanip


@pytest.fixture
def xcconfig_contents():
    return "APP_VERSION = 133.0"


@pytest.fixture
def xcconfig_version():
    return MobileIosVersion.parse("133.0")


def test_get_version_xcconfig(xcconfig_contents, xcconfig_version):
    version = vmanip.get_version(xcconfig_contents, MobileIosVersion, is_xcconfig=True)
    assert version == xcconfig_version


@pytest.mark.asyncio
async def test_bump_version_xcconfig(mocker, github_client):
    branch = "main"
    files = ["firefox-ios/Client/Configuration/version.xcconfig"]
    current_version = "133.0"
    next_version = "134.0"
    file_contents = {files[0]: f"APP_VERSION = {current_version}"}

    mocker.patch.object(github_client, "get_files", return_value=file_contents)

    changes, diff = await vmanip.do_bump_version(github_client, files, next_version, branch)

    assert files[0] in changes
    assert changes[files[0]] == f"APP_VERSION = {next_version}"
    assert f"-APP_VERSION = {current_version}" in diff
    assert f"+APP_VERSION = {next_version}" in diff


@pytest.mark.asyncio
async def test_bump_version_xcconfig_same_version(mocker, github_client):
    branch = "main"
    files = ["firefox-ios/Client/Configuration/version.xcconfig"]
    current_version = "133.0"
    file_contents = {files[0]: f"APP_VERSION = {current_version}"}

    mocker.patch.object(github_client, "get_files", return_value=file_contents)

    changes, diff = await vmanip.do_bump_version(github_client, files, current_version, branch)

    assert changes == {}
    assert diff == ""


@pytest.mark.asyncio
async def test_bump_version_xcconfig_smaller_version(mocker, github_client):
    branch = "main"
    files = ["firefox-ios/Client/Configuration/version.xcconfig"]
    current_version = "133.0"
    next_version = "132.0"
    file_contents = {files[0]: f"APP_VERSION = {current_version}"}

    mocker.patch.object(github_client, "get_files", return_value=file_contents)

    changes, diff = await vmanip.do_bump_version(github_client, files, next_version, branch)

    assert changes == {}
    assert diff == ""
