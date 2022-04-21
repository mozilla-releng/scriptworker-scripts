/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

// If you ever need to force a toolchain rebuild (taskcluster) then edit the following comment.
// FORCE REBUILD 2022-01-13

// Synchronized version numbers for dependencies used by (some) modules
object Versions {
    const val kotlin = "1.5.31"
    const val coroutines = "1.5.2"

    const val junit = "4.12"
    const val robolectric = "4.7.3"
    const val mockito = "3.11.2"
    const val maven_ant_tasks = "2.1.3"

    const val mockwebserver = "3.10.0"

    const val android_gradle_plugin = "7.0.0"
    const val android_maven_publish_plugin = "3.6.2"
    const val lint = "27.0.1"
    const val detekt = "1.19.0"

    const val sentry_legacy = "1.7.21"
    const val sentry_latest = "5.6.1"
    const val okhttp = "3.13.1"
    const val zxing = "3.3.0"
    const val jna = "5.5.0"
    const val disklrucache = "2.0.2"
    const val leakcanary = "2.8.1"

    const val mozilla_appservices = "91.1.0"

    const val mozilla_glean = "44.0.0"

    const val material = "1.2.1"

    const val compose_version = "1.0.5"

}
