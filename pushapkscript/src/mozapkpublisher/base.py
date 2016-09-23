import logging

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
        dash_dash_dict = {'--{}'.format(key.replace('_', '-')): value for key, value in dict_.items()}
        flatten_args = [item for tuples in dash_dash_dict.items() for item in tuples]
        logger.debug('dict_ converveted into these args: %s', flatten_args)
        return flatten_args
