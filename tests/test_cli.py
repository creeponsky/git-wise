import pytest
from click.testing import CliRunner
from git_wise.cli import cli

def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert 'Git-Wise Version:' in result.output