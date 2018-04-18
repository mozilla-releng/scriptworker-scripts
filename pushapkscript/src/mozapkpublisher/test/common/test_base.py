import argparse
import sys

from mozapkpublisher.common.base import Base


class _TestBase(Base):
    @classmethod
    def _init_parser(cls):
        cls.parser = argparse.ArgumentParser(description='Test parser with dummy data')
        cls.parser.add_argument('--a-key')
        cls.parser.add_argument('--k')
        cls.parser.add_argument('--an-int', type=int)


def test_convert_dict_into_args():
    assert Base._convert_dict_into_args({'unary_option': True}) == ['--unary-option']
    assert Base._convert_dict_into_args({'unary_option': False}) == []
    assert Base._convert_dict_into_args({'string_option': 'a_string'}) == ['--string-option', 'a_string']
    assert Base._convert_dict_into_args({
        '*args': ('positional_arg_1', 'positional_arg_2', 'positional_arg_3'),
        'string_option': 'a_string'
    }) == ['--string-option', 'a_string', 'positional_arg_1', 'positional_arg_2', 'positional_arg_3']

    args = Base._convert_dict_into_args({'a_key': 'a_value', 'unary_option': True, 'k': 'v', 'integers_become_strings': 99})
    assert '--a-key', 'a_value' in args
    assert '--k', 'v' in args
    assert '--unary-option' in args
    assert True not in args
    assert '--integers-become-strings', '99' in args


def test_parse_config():
    config = _TestBase._parse_config(config={'a_key': 'a_value', 'k': 'v', 'an_int': 10})
    assert config.a_key == 'a_value'
    assert config.k == 'v'
    assert config.an_int == 10


def test_parse_config_from_argv(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['testcall', '--a-key', 'a_value', '--k', 'v', '--an-int', '10'])
    config = _TestBase._parse_config()
    assert config.a_key == 'a_value'
    assert config.k == 'v'
    assert config.an_int == 10
