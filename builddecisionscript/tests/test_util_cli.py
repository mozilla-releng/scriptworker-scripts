import pytest

import build_decision.util.cli as cli


@pytest.mark.parametrize("raises", (True, False))
def test_cli_main(mocker, raises):
    """Add coverage to util.cli.CLI.main."""

    def fake_command(*args, **kwargs):
        if raises:
            raise Exception("raising")

    fake_parser = mocker.MagicMock()
    fake_args = mocker.MagicMock()
    fake_args.command = fake_command
    fake_parser.parse_args.return_value = fake_args

    class test_cli(cli.CLI):
        def create_parser(self):
            return fake_parser

    c = test_cli("desc")
    if raises:
        with pytest.raises(SystemExit):
            c.main()
    else:
        c.main()
