# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import logging
import sys
import traceback

import attr


@attr.s(cmp=False)
class CLI:
    description = attr.ib(type=str)
    _commands = attr.ib(default=[], init=False)

    def command(self, *args, **kwargs):
        defaults = kwargs.pop("defaults", {})

        def decorator(func):
            self._commands.append((func, args, kwargs, defaults))
            return func

        return decorator

    @staticmethod
    def argument(*names, **kwargs):
        def decorator(func):
            if not hasattr(func, "args"):
                func.args = []
            # Decorators run from bottom to top of the order they were
            # specified in the source. In order to make positional arguments
            # appear in the order they were specifed, we insert arguments at
            # the beginning, so that the list of arguments appears in the same
            # order they were specified in the source.
            func.args.insert(0, (names, kwargs))
            return func

        return decorator

    def create_parser(self):
        parser = argparse.ArgumentParser(description=self.description)
        subparsers = parser.add_subparsers(dest="command")
        subparsers.required = True
        for func, args, kwargs, defaults in self._commands:
            subparser = subparsers.add_parser(*args, **kwargs)
            for arg in getattr(func, "args", []):
                subparser.add_argument(*arg[0], **arg[1])
            subparser.set_defaults(command=func, **defaults)
        return parser

    def main(self):
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
        )
        parser = self.create_parser()
        args = parser.parse_args()
        try:
            args.command(vars(args))
        except Exception:
            traceback.print_exc()
            sys.exit(1)
