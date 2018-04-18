import argparse
import logging

from mozapkpublisher.common.exceptions import WrongArgumentGiven

logger = logging.getLogger(__name__)


class Base(object):
    parser = None

    def __init__(self, config=None):
        self.config = self._parse_config(config)

    @classmethod
    def _parse_config(cls, config=None):
        if cls.parser is None:
            cls._init_parser()

        args = None if config is None else cls._convert_dict_into_args(config)
        # Parses sys.argv if args is None
        return cls.parser.parse_args(args)

    @staticmethod
    def _convert_dict_into_args(dict_):
        # For instance "commit" being True means the argument should be added to the command line.
        dict_without_positional_arguments = {
            key: value for key, value in dict_.items() if key != '*args'
        }
        dict_without_deactivated_unary_arguments = {
            key: value for key, value in dict_without_positional_arguments.items() if value is not False
        }

        dash_dash_dict = {
            '--{}'.format(key.replace('_', '-')): value
            for key, value in dict_without_deactivated_unary_arguments.items()
        }

        args_with_unary_arguments_alone = [
            (key, value) if not isinstance(value, bool) else (key,)
            for key, value in dash_dash_dict.items()
        ]

        flattened_args = [str(item) for tuples in args_with_unary_arguments_alone for item in tuples]
        flattened_args += dict_.get('*args', [])

        logger.debug('dict_ converted into these args: {}'.format(flattened_args))
        return flattened_args


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise WrongArgumentGiven(message)
