import argparse
import logging

from mozapkpublisher.exceptions import WrongArgumentGiven

logger = logging.getLogger(__name__)


class Base(object):
    parser = None

    @classmethod
    def _parse_config(cls, config=None):
        if cls.parser is None:
            cls._init_parser()

        args = None if config is None else cls._convert_dict_into_args(config)
        # Parses sys.argv if args is None
        return cls.parser.parse_args(args)

    @staticmethod
    def _convert_dict_into_args(dict_):
        # For instance "dry_run" being True means the argument should be added to the command line.
        dict_without_deactivated_unary_arguments = {key: value for key, value in dict_.items() if value is not False}

        dash_dash_dict = {
            '--{}'.format(key.replace('_', '-')): value
            for key, value in dict_without_deactivated_unary_arguments.items()
        }

        args_with_unary_arguments_alone = [
            (key, value) if not isinstance(value, bool) else (key,)
            for key, value in dash_dash_dict.items()
        ]

        flatten_args = [str(item) for tuples in args_with_unary_arguments_alone for item in tuples]

        logger.debug('dict_ converted into these args: {}'.format(flatten_args))
        return flatten_args


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise WrongArgumentGiven(message)
