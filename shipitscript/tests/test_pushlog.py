import pytest

import shipitscript.pushlog_scan as pushlog


@pytest.mark.parametrize(
    "branch,last_shipped_rev,cron_rev,ret_json,shippable_rev",
    [
        (
            "releases/mozilla-beta",
            "38fc7c5ed55f4bdbdc837e11bb67eb6bfde947c9",
            "2691dbbedf8783bfccbeba8dc6296bc3d7750285",
            {
                "12629": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "1cb76ecda563b998b1f43c3dcaa0dc0fbcee09ab",
                        }
                    ]
                },
                "12630": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "d3ab563a434bfafa13aaad2dcde764104367336a",
                        }
                    ]
                },
                "12631": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "4384aff21707cbe182552fac12c80e501c2a5347",
                        }
                    ]
                },
                "12632": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "4a5ccaf952f36ab2d4fb964846070a064332fede",
                        }
                    ]
                },
                "12633": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "cc15292b43c8d1464b08f23d506854dc280afaed",
                        }
                    ]
                },
                "12634": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "3b533b3307f458b0e49419885727e48e59b1676a",
                        }
                    ]
                },
                "12635": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "7836b5c808d716e25d0e104e56ffe6b6d1769093",
                        }
                    ]
                },
                "12636": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "63e9ec6137a98211b3f0382223af9f7b76cb8751",
                        }
                    ]
                },
                "12637": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "1ec50e8f87beab6dcfe7bf2a6d16c40d1bab2fcc",
                        }
                    ]
                },
                "12638": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "9acdddba74865e566fe3b3c3fe02e68aa5b1cfcb",
                        }
                    ]
                },
                "12639": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 38fc7c5ed55f4bdbdc837e11bb67eb6bfde947c9 with DEVEDITION_73_0b10_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "b99b6569fdebd74b544f553fa723720677b6894f",
                        }
                    ]
                },
                "12640": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 38fc7c5ed55f4bdbdc837e11bb67eb6bfde947c9 with FIREFOX_73_0b10_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "fcd57d8c15f69267c5de64f989d765b96b44c5cb",
                        }
                    ]
                },
                "12641": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 38fc7c5ed55f4bdbdc837e11bb67eb6bfde947c9 with DEVEDITION_73_0b10_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "24221e3de3eeaaf6d3d5b4105816bfe27a643a50",
                        },
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "Automatic version bump CLOSED TREE NO BUG a=release DONTBUILD",
                            "node": "d0ecc6fc32a8f0e1cfb21be5f27ce65fb11901d8",
                        },
                    ]
                },
                "12642": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "2d2c23ffd72e0eb31df7d580586b61c13dfe89c7",
                        }
                    ]
                },
                "12643": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 38fc7c5ed55f4bdbdc837e11bb67eb6bfde947c9 with FIREFOX_73_0b10_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "615eef30e3a4e600f815a79e38ad868a774a3e01",
                        }
                    ]
                },
                "12644": {
                    "changesets": [
                        {
                            "author": "Neil Deakin <neil@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1603020, to send the message to all descendants, not just process roots, r=mconley, a=jcristau",
                            "node": "be4754a40d8efa09060e69fb41001e2a16445a09",
                        },
                        {
                            "author": "Neil Deakin <neil@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1603020, send state update messages to all child actors, r=mikedeboer, a=jcristau",
                            "node": "d7efce5292008023a265e3c025c8dc22b8fb1434",
                        },
                        {
                            "author": "Andrea Marchesini <amarchesini@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1608373 - proxy webExtension API should not expose extensions, r=mixedpuppy, a=jcristau",
                            "node": "bcd62affb1c3c64cb6a28ae1964d5e62749fbac3",
                        },
                        {
                            "author": "Nihanth Subramanya <nhnt11@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1605297 - Don't expect telemetry after restarting add-on in policy override test. r=johannh, a=test-only",
                            "node": "c24dfbda267ec738479bdc63ac6cfad60212d8dc",
                        },
                    ]
                },
                "12645": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "a2273533849ae089e19d13821f32928e6b475027",
                        }
                    ]
                },
                "12646": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "ed18b0818d433d7ed29c58c77f9d9a77c6b06e06",
                        }
                    ]
                },
                "12647": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "2691dbbedf8783bfccbeba8dc6296bc3d7750285",
                        }
                    ]
                },
            },
            "c24dfbda267ec738479bdc63ac6cfad60212d8dc",
        ),
        (
            "releases/mozilla-beta",
            "c24dfbda267ec738479bdc63ac6cfad60212d8dc",
            "efdc710721d690d0629ccd17651d7a2885fd3d60",
            {
                "12645": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "a2273533849ae089e19d13821f32928e6b475027",
                        }
                    ]
                },
                "12646": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "ed18b0818d433d7ed29c58c77f9d9a77c6b06e06",
                        }
                    ]
                },
                "12647": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "2691dbbedf8783bfccbeba8dc6296bc3d7750285",
                        }
                    ]
                },
                "12648": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging c24dfbda267ec738479bdc63ac6cfad60212d8dc with DEVEDITION_73_0b11_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "2f66a4fa931a6676992323c2136de25f9a76a898",
                        }
                    ]
                },
                "12649": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging c24dfbda267ec738479bdc63ac6cfad60212d8dc with FIREFOX_73_0b11_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "06496a21f73237f6aec8a72127e87021d611d122",
                        }
                    ]
                },
                "12650": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging c24dfbda267ec738479bdc63ac6cfad60212d8dc with DEVEDITION_73_0b11_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "778de3ff9bae40d264fd51d3ee77b3cdf37f2b74",
                        },
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "Automatic version bump CLOSED TREE NO BUG a=release DONTBUILD",
                            "node": "87622946bf30d9b9457bf9475c378e41426661c1",
                        },
                    ]
                },
                "12651": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging c24dfbda267ec738479bdc63ac6cfad60212d8dc with FIREFOX_73_0b11_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "85cadca54d982bef3472d26c0c02b01b80c28183",
                        }
                    ]
                },
                "12652": {
                    "changesets": [
                        {
                            "author": "Hiroyuki Ikezoe <hikezoe.birchill@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1611561 - Fix the return value of the in nsFocusManager::ActivateOrDeactivate. r=smaug, a=jcristau",
                            "node": "0ed7855a2e0368849868556ee2c17952bc54bc6a",
                        },
                        {
                            "author": "Jan-Ivar Bruaroey <jib@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1598543 - Use size instead of length. r=dminor, a=jcristau",
                            "node": "e07c1d22ec2f4b41a5bc1fc3f76f853248d82ff6",
                        },
                        {
                            "author": "Jan-Ivar Bruaroey <jib@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1598543 - Cleanup upstream constants to also use size instead of length. r=dminor, a=jcristau",
                            "node": "6cbc2116abb44096653127df74bdbd8fd39d0baa",
                        },
                    ]
                },
                "12653": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "8c0af6f2e44703a8ba2a9567c9e8b529ac853d44",
                        }
                    ]
                },
                "12654": {
                    "changesets": [
                        {
                            "author": "Paul Adenot <paul@paul.cx>",
                            "branch": "default",
                            "desc": "Bug 1609400 - Lock when setting a graph's current driver. r=achronop a=jcristau",
                            "node": "ff04ad75dcd24112343510b5644946ed81b9467f",
                        }
                    ]
                },
                "12655": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "cd1c43b6913dadfb3e60abb98d769deae15b1f8a",
                        }
                    ]
                },
                "12656": {
                    "changesets": [
                        {
                            "author": "Jeff Walden <jwalden@mit.edu>",
                            "branch": "default",
                            "desc": "Bug 1596706.  r=tcampbell a=jcristau",
                            "node": "23ec77327b8f310b33bb64f928488c3999c67300",
                        },
                        {
                            "author": "Matthew Gregan <kinetik@flim.org>",
                            "branch": "default",
                            "desc": "Bug 1610647 - Revert unintentionally re-enabled IAudioClient3.  r=achronop a=jcristau",
                            "node": "f01dc6936ff409fdc359142f69d0aac15a974fdc",
                        },
                    ]
                },
                "12657": {
                    "changesets": [
                        {
                            "author": "Simon Giesecke <sgiesecke@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1612289 - Remove IDBTransaction.commit implementation is only a stub. r=emilio,asuth a=jcristau",
                            "node": "14ac73797dd828cc30a99df36befbec79069bde4",
                        }
                    ]
                },
                "12658": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 14ac73797dd828cc30a99df36befbec79069bde4 with DEVEDITION_73_0b12_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "5e7f49eb480ef02a29e837f4df29d240b7934956",
                        }
                    ]
                },
                "12659": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 14ac73797dd828cc30a99df36befbec79069bde4 with FIREFOX_73_0b12_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "76eff308e8325b619065a873fd3537f65611dd6e",
                        }
                    ]
                },
                "12660": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 14ac73797dd828cc30a99df36befbec79069bde4 with DEVEDITION_73_0b12_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "1cd1c9a85c97db94db5d0effc6db12577092299c",
                        },
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "Automatic version bump CLOSED TREE NO BUG a=release DONTBUILD",
                            "node": "efdc710721d690d0629ccd17651d7a2885fd3d60",
                        },
                    ]
                },
            },
            "14ac73797dd828cc30a99df36befbec79069bde4",
        ),
        (
            "releases/mozilla-beta",
            "6a9e651e08318cd1a5da7f1bc2b489e47d4acf3f",
            "3f19dfb367d6f5418554b52997592a49a2c47f99",
            {
                "12595": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 6a9e651e08318cd1a5da7f1bc2b489e47d4acf3f with DEVEDITION_73_0b8_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "4240721f89cdc5fd90a55e1f2d5a710a15fc808e",
                        }
                    ]
                },
                "12596": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 6a9e651e08318cd1a5da7f1bc2b489e47d4acf3f with FIREFOX_73_0b8_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "5d5df9bb8da464f2d3aa9c119574c29ae734caeb",
                        }
                    ]
                },
                "12597": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 6a9e651e08318cd1a5da7f1bc2b489e47d4acf3f with DEVEDITION_73_0b8_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "6f727fe59b92319e2fa4f8e31ec1be25cf7909be",
                        },
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "Automatic version bump CLOSED TREE NO BUG a=release DONTBUILD",
                            "node": "cf29c7ebb6bd85af3ceef58e524ca4d3e48d9b94",
                        },
                    ]
                },
                "12598": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging 6a9e651e08318cd1a5da7f1bc2b489e47d4acf3f with FIREFOX_73_0b8_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "9cf60bcf654f25f9592ba84547981d76fe5affc9",
                        }
                    ]
                },
                "12599": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "f536e83f921bda52757fa47b74b3b0c8045710d7",
                        }
                    ]
                },
                "12600": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "d021f158604f0386662d49c33c548c6937d5e3e1",
                        }
                    ]
                },
                "12601": {
                    "changesets": [
                        {
                            "author": "Johann Hofmann <jhofmann@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1591362 - Fix incorrect origin comparison in r=baku,mayhemer,michal, a= RyanVM",
                            "node": "3e32cd5df849fba770112509514e973da55ee63d",
                        },
                        {
                            "author": "Nihanth Subramanya <nhnt11@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1600109 - Implement setup function in js in all tests. r=dragana,JuniorHsu, a=RyanVM",
                            "node": "80a41f935b680a1bc763abad85443feed5bc3052",
                        },
                        {
                            "author": "Nihanth Subramanya <nhnt11@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1600109 - Fix network change handling and test telemetry. r=dragana, a=RyanVM",
                            "node": "9fa4497af594cdf7e5497eef3e4e5e68bfde25f6",
                        },
                        {
                            "author": "Toshihito Kikuchi <tkikuchi@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1604008 - Use a target process's export table to cross-process detour.  r=aklotz, a=RyanVM",
                            "node": "ae3ffb3ccd34d2924fe109db19b03bb34622c3cb",
                        },
                        {
                            "author": "D\u00e3o Gottwald <dao@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1607160 - Skip positioned elements when calculating whether a toolbar overflows. r=Gijs, a=RyanVM",
                            "node": "738788c6b5888f51051d9c1155c58af5d0d3cca3",
                        },
                        {
                            "author": "Alex Chronopoulos <achronop@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1608118 - Remove direct listeners from the source in MediaInput is removed r=padenot, a=RyanVM",
                            "node": "677842171b3976dfd8cceef0fbd0e67438138df8",
                        },
                        {
                            "author": "Nihanth Subramanya <nhnt11@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1608320 - DoH Rollout Extension: Don't show the the post-DoH privacy statement. r=dragana, a=RyanVM",
                            "node": "c2bec0f6c3180bc8efb2e5955df97e48ed47b69d",
                        },
                        {
                            "author": "Toshihito Kikuchi <tkikuchi@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1608645 - Ensure FindExportAddressTableEntry can handle a modified Export Table.  r=aklotz, a=RyanVM",
                            "node": "2d569074605c1cf34d63abd6f452b3ea524f2688",
                        },
                        {
                            "author": "Nihanth Subramanya <nhnt11@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1609037 - DoH Rollout Extension: Wait until a top-level location change to shodoorhanger. r=johannh, a=RyanVM",
                            "node": "1766ab40038c5537e360eb6569b91f0bf26a6e4b",
                        },
                        {
                            "author": "Daisuke Akatsuka <daisuke@birchill.co.jp>",
                            "branch": "default",
                            "desc": "Bug 1609348: Set minSize to SplitBox. r=miker, a=RyanVM",
                            "node": "fdee6b043befeda754fd348bb40267d63e5e525d",
                        },
                        {
                            "author": "Morgan Reschenberg <mreschenberg@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1610250: Ensure we compare rounded integer values when setting the hidden bar's zoom button. r=Gijs, a=RyanVM",
                            "node": "ad0b96ec1b63f55f6d30312d2a8c1d6858e31e77",
                        },
                        {
                            "author": "Andrew Osmond <aosmond@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1610381 - Improve image memory reporting for missing/incomplete surfaces. r=tnikkel, a=RyanVM",
                            "node": "f18a1b991e0c661fde00ea306a16f735beee6fda",
                        },
                        {
                            "author": "Andrew Osmond <aosmond@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1610381 - Part 2. Improve image memory reporting with more state information. r=jrmuizel, a=RyanVM",
                            "node": "c3b49b0d837afb08288e969106c39eff0bb7fe0e",
                        },
                        {
                            "author": "Andrew Osmond <aosmond@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1610381 - Part 3. Improve image memory reporting by including validation state. r=jrmuizel, a=RyanVM",
                            "node": "eeeb6d082bbca0637530c603ef16f9f0e29ebdc2",
                        },
                        {
                            "author": "Jeff Muizelaar <jrmuizel@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1610912. Prevent double buffering from riding the trains. r=aosmond, a=RyanVM",
                            "node": "c5885a995c9dd9bc06143c0a565782807f56bbe8",
                        },
                        {
                            "author": "Byron Campen [:bwc] <docfaraday@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1605128: Make websocket_process_bridge less picky about the version of six it wants. r=ahal, a=test-only",
                            "node": "19f907e7821827594e1ad24bf74c3e8c83f998ba",
                        },
                    ]
                },
                "12602": {
                    "changesets": [
                        {
                            "author": "Morgan Reschenberg <mreschenberg@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1609581: Ensure backplates inherit color from nearest color select multiple's. r=emilio, a=RyanVM",
                            "node": "de521b37210e82f9ee456af47d6c6ee4c29f7104",
                        },
                        {
                            "author": "Perry Jiang <perry@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1601024 - ThreadSafeWeakReference::tryDetach must acquire its lock. r=froydnj, a=RyanVM",
                            "node": "d358769894d0ab96bb76507ffab5a41733865f20",
                        },
                        {
                            "author": "Perry Jiang <perry@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1609665 - promote diagnostic assert to release assert. r=asuth, a=RyanVM",
                            "node": "eca62a891f1d121f911cfa95b7430a648da30f54",
                        },
                        {
                            "author": "Perry Jiang <perry@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1409979 - ExtendableEvent.waitUntil should account for dispatch flag. r=asuth, a=RyanVM",
                            "node": "d28702c59e9a7eb2895b06fe007853df4d7eb8e9",
                        },
                        {
                            "author": "Tim Nguyen <ntim.bugs@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1610597 - Use legacy-stack for notification boxes. r=bgrins, a=RyanVM",
                            "node": "cfec84ed397727c9e35e6c1ead0df46be53ad246",
                        },
                    ]
                },
                "12603": {
                    "changesets": [
                        {
                            "author": "Ryan VanderMeulen <ryanvm@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1609581 - Update reftest fuzz annotations. a=bustage",
                            "node": "1876c9081e6db77a367ae52bb9cdca7bebc98f37",
                        }
                    ]
                },
                "12604": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "e85617d6aebc3aaae260bf1ced83d34cda8dad7d",
                        }
                    ]
                },
                "12605": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "75974fd949c55291ac62e9d237fa6e68f6dac527",
                        }
                    ]
                },
                "12606": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "5eb0c2824aec0a4421fcb63cbfc5b9d3658cf360",
                        }
                    ]
                },
                "12607": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "776f2f89d3dd89ce800b081fea7c4463b155a627",
                        }
                    ]
                },
                "12608": {
                    "changesets": [
                        {
                            "author": "Christoph Kerschbaumer <ckerschb@christophkerschbaumer.com>",
                            "branch": "default",
                            "desc": "Bug 1610572: Disable Feature Policy for FF73. r=johannh a=RyanVM",
                            "node": "808ea709938d45c81692145716fdc8c487828299",
                        }
                    ]
                },
                "12609": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "b6ff51d0d22e0afb3c997d49ce71015488149ff0",
                        }
                    ]
                },
                "12610": {
                    "changesets": [
                        {
                            "author": "Mihai Alexandru Michis <malexandru@mozilla.com>",
                            "branch": "default",
                            "desc": "Backed out changeset 418f08a73850 (bug 1599606) for causing Bug 1609022. a=RyanVM",
                            "node": "2af9f10b709417fcac5d826b160e0f23f14e3d31",
                        }
                    ]
                },
                "12611": {
                    "changesets": [
                        {
                            "author": "Tom Prince <mozilla@hocat.ca>",
                            "branch": "default",
                            "desc": "Bug 1547111: Remove incorrect GCP sccache scope; r=Callek a=tomprince",
                            "node": "9c59a17ad5ec8219108d3aecd756f3bf0fafd7f9",
                        }
                    ]
                },
                "12612": {
                    "changesets": [
                        {
                            "author": "ffxbld <ffxbld@mozilla.com>",
                            "branch": "default",
                            "desc": "No Bug, mozilla-beta repo-update HSTS HPKP blocklist remote-settings - a=repo-update r=RyanVM",
                            "node": "060a20420d6ef05e06f855cf4d1d1ca9b1827073",
                        },
                        {
                            "author": "Eugen Sawin <esawin@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1609701 - [1.1] Ignore resuming of non-suspended windows. r=smaug, a=RyanVM",
                            "node": "7e43babbd70685c76d50f8466b0ed89a99a0209f",
                        },
                    ]
                },
                "12613": {
                    "changesets": [
                        {
                            "author": "Andrew Creskey <acreskey@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1591725 - Optimize at -O2 on android, clang. r=froydnj,dmajor, a=RyanVM",
                            "node": "c270bc80557a52d64796167aa11798fb0961cfaf",
                        }
                    ]
                },
                "12614": {
                    "changesets": [
                        {
                            "author": "Ryan VanderMeulen <ryanvm@gmail.com>",
                            "branch": "default",
                            "desc": "Backed out changeset c270bc80557a (bug 1591725)",
                            "node": "adaa66ecae24973f1a75d2d955024b64ba192f7b",
                        }
                    ]
                },
                "12615": {
                    "changesets": [
                        {
                            "author": "Gabriele Svelto <gsvelto@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1610426 - Discard unknown crash annotations. r=froydnj, a=RyanVM",
                            "node": "8f3b8fef5686e74c42651602ed4f73a561680d86",
                        },
                        {
                            "author": "Ryan VanderMeulen <ryanvm@gmail.com>",
                            "branch": "default",
                            "desc": "Backed out changeset 2d569074605c (bug 1608645) for causing bug 1610790.",
                            "node": "404293e0e5aa9d117d265cfeb9b5e8fec99ebd13",
                        },
                        {
                            "author": "Ryan VanderMeulen <ryanvm@gmail.com>",
                            "branch": "default",
                            "desc": "Backed out changeset ae3ffb3ccd34 (bug 1604008) to avoidfrom bug 1608645 being backed out.",
                            "node": "6fa1f4dcb6b14ac9a0430a650a3171ac893cc0bf",
                        },
                        {
                            "author": "Michael Froman <mfroman@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1609417 - Don't treat 0 size samples as an error in DecodeNextSample. r=jya, a=RyanVM",
                            "node": "14886e51af43ff8e30d1fc71ff92e8c2ec43b2ef",
                        },
                        {
                            "author": "Tom Ritter <tom@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1609474 - Handle if extensions.webextensions.remote Eval/JS Load Telemetry. r=robwu,ckerschb, a=RyanVM",
                            "node": "9fb939d53102640167c3e8162e93f0b6535e5252",
                        },
                    ]
                },
                "12616": {
                    "changesets": [
                        {
                            "author": "Jan Varga <jan.varga@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1608449 - Disable LSNG in 73. r=asuth, a=RyanVM",
                            "node": "25e854c968684e49838c9048bfb6d66222945914",
                        }
                    ]
                },
                "12617": {
                    "changesets": [
                        {
                            "author": "J.C. Jones <jc@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1611207 - Land NSS NSS_3_49_2_RTM UPGRADE_NSS_RELEASE. r=kjacobs, a=RyanVM",
                            "node": "05488f75f774a2944e9b4abec1066e5c1c73b261",
                        },
                        {
                            "author": "Gijs Kruitbosch <gijskruitbosch@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1609257 - Only read flash only pref in automation. r=handyman, a=RyanVM",
                            "node": "a97b7233686470f3fcd51e64a18f72d8e80e1356",
                        },
                    ]
                },
                "12618": {
                    "changesets": [
                        {
                            "author": "Ryan VanderMeulen <ryanvm@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1610888 - Disable DocumentChannel and SW-e10s. r=mattwoodrow, a=RyanVM",
                            "node": "3f19dfb367d6f5418554b52997592a49a2c47f99",
                        }
                    ]
                },
            },
            "3f19dfb367d6f5418554b52997592a49a2c47f99",
        ),
        (
            "releases/mozilla-beta",
            "fe6f34b2859f0706c88ec07199e30395041af258",
            "6a9e651e08318cd1a5da7f1bc2b489e47d4acf3f",
            {
                "12581": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "4377cc64189b274eb377b6c0efe3a33f897e0fe7",
                        }
                    ]
                },
                "12582": {
                    "changesets": [
                        {
                            "author": "Kris Maglione <maglione.k@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1603014: Wait for content tasks to add listener before triggering things they're listening for. r=mccr8 a=test-only",
                            "node": "a18bcd9f3a774aafafdf0ab7f3d7c62f9f5cdb08",
                        },
                        {
                            "author": "shindli <shindli@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1603014 - unskip browser_pdfjs_zoom.js on mac r=jmaher a=test-only",
                            "node": "2ddff55d937472f634413c0bc7daaad512ea314b",
                        },
                        {
                            "author": "Andrew McCreight <continuation@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1608575 - Disable browser_windowProxy_transplant.js when Fission is disabled on Linux and OSX. r=kmag a=test-only",
                            "node": "e7f513315a2a6278129d89beb93c7641c36e2394",
                        },
                    ]
                },
                "12583": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging fe6f34b2859f0706c88ec07199e30395041af258 with FIREFOX_73_0b7_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "a0a0f32dba9cd1206e37ff8a97715ef255ed2a8d",
                        }
                    ]
                },
                "12584": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging fe6f34b2859f0706c88ec07199e30395041af258 with DEVEDITION_73_0b7_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "b3a29e2b01f7ce130f337e49aa92f050e2af5551",
                        }
                    ]
                },
                "12585": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging fe6f34b2859f0706c88ec07199e30395041af258 with FIREFOX_73_0b7_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "99e5daac64fbd8153d336ee787b21ea0163c2878",
                        },
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "Automatic version bump CLOSED TREE NO BUG a=release DONTBUILD",
                            "node": "efbdab562791713870931c8b2f394bf8dd5e6724",
                        },
                    ]
                },
                "12586": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging fe6f34b2859f0706c88ec07199e30395041af258 with DEVEDITION_73_0b7_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "03106a2f5c256c36f25755249d6bf2d67f696915",
                        }
                    ]
                },
                "12587": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "a57612f6d5b755787c7541b470fe7712cd9ec790",
                        }
                    ]
                },
                "12588": {
                    "changesets": [
                        {
                            "author": "Gijs Kruitbosch <gijskruitbosch@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1600919 - work around XUL layout bug by manually measuring wrapping dialog, r=MattN,zbraniecki a=RyanVM",
                            "node": "6436bededa92f55671640d4b1a1e8afb3cad9220",
                        },
                        {
                            "author": "Jon Coppeard <jcoppeard@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1291535 - Clear the list of dynamic import requests after do for other requests r=bzbarsky a=RyanVM",
                            "node": "fa2485dac022dc0ce1f58ab58531fcc94ca7e031",
                        },
                        {
                            "author": "Marco Bonardo <mbonardo@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1605889 - Ensure LTR origins stay visible on urlbar blur. r=dao a=RyanVM",
                            "node": "21851727fe14bd17b2f17238e1c4b6fe59acf826",
                        },
                        {
                            "author": "ffxbld <ffxbld@mozilla.com>",
                            "branch": "default",
                            "desc": "No Bug, mozilla-beta repo-update HSTS HPKP blocklist remote-settings - r=RyanVm a=repo-update",
                            "node": "46a918bc815fbb36b4297d624870858e7ab358eb",
                        },
                    ]
                },
                "12589": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "892139b214c04ad703e95e19a5191a0f05fcfa06",
                        }
                    ]
                },
                "12590": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "786c4a7ee5af0190433bf661ab13a7a49a5bc2c7",
                        }
                    ]
                },
                "12591": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Firefox l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "280f5fee256a7a8c299c5f2220c5eb1a1abcb738",
                        }
                    ]
                },
                "12592": {
                    "changesets": [
                        {
                            "author": "Scott <scott.downe@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1609160 - Search only logo displayed with just highlights. a=RyanVM",
                            "node": "ebc9e423325028b246dc1f49937fbdd268eca893",
                        },
                        {
                            "author": "Michael Kaply <345868+mkaply@users.noreply.github.com>",
                            "branch": "default",
                            "desc": "Bug 1607937 - If an origin is blocked, show the custom policy message if it is there. r=mixedpuppy a=RyanVM",
                            "node": "f93792dc51d8acb7c95534572aa4fb4049520db6",
                        },
                        {
                            "author": "Jeff Muizelaar <jrmuizel@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1604800. Revert Bug 1604180 and Bug 1598582. a=RyanVM",
                            "node": "83cf7cb85a9fe32f0f10fabcfb2f1a071cee3cec",
                        },
                        {
                            "author": "Zibi Braniecki <zbraniecki@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1607111 - Use BCP47 lang tags for negotiation in content process. r=jfkthame a=RyanVM",
                            "node": "c6da7fb980c3e4acdf8d03f1c988e5a7d8560b1e",
                        },
                        {
                            "author": "Gijs Kruitbosch <gijskruitbosch@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1608923 - reuse some DTD strings so at least play/pause and the mute/unmute button are labeled, r?mconley a=RyanVM",
                            "node": "0c95299ef20e4b5e9f907b5c56387cebe7621147",
                        },
                        {
                            "author": "Michael Kaply <345868+mkaply@users.noreply.github.com>",
                            "branch": "default",
                            "desc": "Bug 1603221 - Use isCertTrusted instead of asyncVerify to check for policy installed certs. r=keeler a=RyanVM",
                            "node": "75a81bd77eae12945e1949877a46c90f10b7db8a",
                        },
                        {
                            "author": "Andrew Osmond <aosmond@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1600472 - Disable allowing sacrificing subpixel anti-aliasing for small screens. r=jrmuizel a=RyanVM",
                            "node": "680eace9a704b3e55f9df7c6592e6284d68ea7cd",
                        },
                        {
                            "author": "Masayuki Nakano <masayuki@d-toybox.com>",
                            "branch": "default",
                            "desc": "Bug 1583135 - Disable scroll-anchoring at all editable elements r=emilio a=RyanVM",
                            "node": "bad956e1a146b72ca60e2639fc33f5cac91d26fe",
                        },
                    ]
                },
                "12593": {
                    "changesets": [
                        {
                            "author": "Jean-Yves Avenard <jyavenard@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1606901 - Test that channel is still opened before continuing. r=mattwoodrow, a=RyanVM",
                            "node": "484e2cc7166ccafa0f8c4afe0d42a484a1eff217",
                        }
                    ]
                },
                "12594": {
                    "changesets": [
                        {
                            "author": "Micah Tigley <mtigley@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1608003 - Enable event bubbling when dispatching simulated touch events. r=bradwerth, a=RyanVM",
                            "node": "ad394fc354aea6741936257aa3ef3f7d3ffd7eb0",
                        },
                        {
                            "author": "Micah Tigley <mtigley@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1608003 - Make touch event test assume only the old RDM UI. r=bradwerth, a=RyanVM",
                            "node": "44b1b0ca0f28f28275a6e95b124d340b0b5f47c8",
                        },
                        {
                            "author": "Tim Nguyen <ntim.bugs@gmail.com>",
                            "branch": "default",
                            "desc": "Bug 1610152 - Ensure extension browsers take at least their parent's min-height. r=Gijs, a=RyanVM",
                            "node": "ba2d89bc5efcfb958b933a2d26fccd3e95f22011",
                        },
                        {
                            "author": "Daisuke Akatsuka <daisuke@birchill.co.jp>",
                            "branch": "default",
                            "desc": "Bug 1609330: Fix the graph height and the location. r=miker, a=RyanVM",
                            "node": "6a9e651e08318cd1a5da7f1bc2b489e47d4acf3f",
                        },
                    ]
                },
            },
            "6a9e651e08318cd1a5da7f1bc2b489e47d4acf3f",
        ),
        (
            "releases/mozilla-esr68",
            "d8e217ff942c17a15075e6cd4ec0f33b095f45fd",
            "5b60ba8829c01de0197b4154a5bc8b89e01defbc",
            {
                "810": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "ba33f311ab4eed012e11796cdbc0869e9a4e4f19",
                        }
                    ]
                },
                "811": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "d7c6d6749a33fa3a357cf11e2851cd203e8c38e6",
                        }
                    ]
                },
                "812": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "c9b3ed55b6479c770508ad12a585ef8f924bf177",
                        }
                    ]
                },
                "813": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "3d9b07c0cac405192178595023f06a4ec2db49ff",
                        }
                    ]
                },
                "814": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "219830e0e1bce87e8512950a05f4b686d4811fe1",
                        }
                    ]
                },
                "815": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "2f2500ee0c26f6aff9bd8e865b9e60c194df4744",
                        }
                    ]
                },
                "816": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "46750df66da6ccc713ab38d72fd427da3e306bf7",
                        }
                    ]
                },
                "817": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "85f0b3c979e69f42108b733ca421fb0e59590b4e",
                        }
                    ]
                },
                "818": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging d8e217ff942c17a15075e6cd4ec0f33b095f45fd with FENNEC_68_5b5_BUILD1 a=release CLOSED TREE DONTBUILD",
                            "node": "a524dd30c886aca5abebcdc2a17a990b1aef9745",
                        }
                    ]
                },
                "819": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "5712357789455899f68fa76decc5dbfc6c6d371b",
                        }
                    ]
                },
                "820": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "No bug - Tagging d8e217ff942c17a15075e6cd4ec0f33b095f45fd with FENNEC_68_5b5_RELEASE a=release CLOSED TREE DONTBUILD",
                            "node": "b2160e5b04ed4603b1ca0209e1da34f97c59cdf1",
                        },
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "Automatic version bump CLOSED TREE NO BUG a=release DONTBUILD",
                            "node": "ee17bdeedc019c282398972d6a57ff2c497704fa",
                        },
                    ]
                },
                "821": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "5ec31d8d1f5ecc8816ae497d08a60c8f6bc0e78b",
                        }
                    ]
                },
                "822": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "cd03c1d153170133a945392da97e43eb2e381cc4",
                        }
                    ]
                },
                "823": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "e1268329b7d6f2a687737a7d0a0bd03bfb3a207f",
                        }
                    ]
                },
                "824": {
                    "changesets": [
                        {
                            "author": "Eitan Isaacson <eitan@monotonous.org>",
                            "branch": "default",
                            "desc": "Bug 1534287 - Catch exception when platform a11y is disabled. r=geckoview-reviewers,snorp, a=jcristau",
                            "node": "bfbf484ecbccdf60a2b265e67db3012982a88868",
                        },
                        {
                            "author": "Bryce Van Dyk <bvandyk@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1596894 - Update fallback GMP downloader for Widevine 4.10.1582.2. r=rhelmer, a=jcristau",
                            "node": "6e380e9e61a1c5f5bf26db7134d5c6e024a65741",
                        },
                        {
                            "author": "Jan-Ivar Bruaroey <jib@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1598543 - Use size instead of length. r=dminor, a=jcristau",
                            "node": "f754db38b851b49fdb08312e8e929e8f0793f6ee",
                        },
                        {
                            "author": "Jan-Ivar Bruaroey <jib@mozilla.com>",
                            "branch": "default",
                            "desc": "Bug 1598543 - Cleanup upstream constants to also use size instead of length. r=dminor, a=jcristau",
                            "node": "231b92b1db0a354ac3f6356c1fad1342711580c1",
                        },
                        {
                            "author": "Petru Lingurar <petru.lingurar@softvision.ro>",
                            "branch": "default",
                            "desc": "Bug 1610873 - Check for null before calling instance methods; r=VladBaicu, a=jcristau",
                            "node": "fac95027fda1540460a05a2f6b05210a14e60293",
                        },
                    ]
                },
                "825": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "cb6d27646603a1205355f974ca6addb61e4c01b3",
                        }
                    ]
                },
                "826": {
                    "changesets": [
                        {
                            "author": "Kai Engert <kaie@kuix.de>",
                            "branch": "THUNDERBIRD_68_VERBRANCH",
                            "desc": "Bug 1606619 - Fix Firefox CVE-2018-12383 in Thunderbird, cleanup key3.db if migration is known to have succeeded.",
                            "node": "661669a9175b755a43bde8a1a6594cd93f3f75df",
                        }
                    ]
                },
                "827": {
                    "changesets": [
                        {
                            "author": "Mozilla Releng Treescript <release+treescript@mozilla.org>",
                            "branch": "default",
                            "desc": "no bug - Bumping Fennec l10n changesets r=release a=l10n-bump DONTBUILD",
                            "node": "5b60ba8829c01de0197b4154a5bc8b89e01defbc",
                        }
                    ]
                },
            },
            "fac95027fda1540460a05a2f6b05210a14e60293",
        ),
    ],
)
def test_get_shippable_revision_build(requests_mock, branch, last_shipped_rev, cron_rev, ret_json, shippable_rev):
    requests_mock.get(pushlog.URL.format(branch=branch), json=ret_json)
    assert pushlog.get_shippable_revision_build(branch, last_shipped_rev, cron_rev) == shippable_rev
