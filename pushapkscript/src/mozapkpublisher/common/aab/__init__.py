import argparse

from mozapkpublisher.common.aab.extractor import extract_metadata


def add_aab_checks_arguments(parser):
    parser.add_argument('aabs', metavar='path_to_aab', type=argparse.FileType(mode='rb'), nargs='+',
                        help='The path to the AAB to upload.')


def extract_aabs_metadata(
    aabs,
):
    aabs_metadata = {
        aab: extract_metadata(aab.name)
        for aab in aabs
    }

    return aabs_metadata
