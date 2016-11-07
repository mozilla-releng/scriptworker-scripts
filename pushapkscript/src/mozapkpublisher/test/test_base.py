import argparse
import sys

from mozapkpublisher.base import Base


class TestBase(Base):
    @classmethod
    def _init_parser(cls):
        cls.parser = argparse.ArgumentParser(description='Test parser with dummy data')
        cls.parser.add_argument('--a-key')
        cls.parser.add_argument('--k')


def test_convert_dict_into_args():
    assert Base._convert_dict_into_args({'unary_option': True}) == ['--unary-option']
    assert Base._convert_dict_into_args({'unary_option': False}) == []
    assert Base._convert_dict_into_args({'string_option': 'a_string'}) == ['--string-option', 'a_string']

    args = Base._convert_dict_into_args({'a_key': 'a_value', 'unary_option': True, 'k': 'v', 'integers_become_strings': 99})
    assert '--a-key', 'a_value' in args
    assert '--k', 'v' in args
    assert '--unary-option' in args
    assert True not in args
    assert '--integers-become-strings', '99' in args


def test_parse_config():
    config = TestBase._parse_config(config={'a_key': 'a_value', 'k': 'v'})
    assert config.a_key == 'a_value'
    assert config.k == 'v'


def test_parse_config_from_argv(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['testcall', '--a-key', 'a_value', '--k', 'v'])
    config = TestBase._parse_config()
    assert config.a_key == 'a_value'
    assert config.k == 'v'
