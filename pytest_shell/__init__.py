# -*- coding: utf-8 -*-

import pytest


@pytest.fixture(name='bash')
def bash_fixture(request):
    from pytest_shell.shell import bash
    with bash() as b:
        yield b
