# -*- coding: utf-8 -*-
import pytest

from pytest_shell.shell import bash


def test_basic_command(testdir):
    with bash() as s:
        s.send('ls /')


def test_inline_script_error(testdir):
    testdir.makepyfile("""
        def test_inline_script_error(bash):
            import pytest
            out = bash.run_script_inline(['fsad'])
    """)
    result = testdir.runpytest()
    assert result.ret != 0


def test_script(testdir):
    testdir.makepyfile("""
        def test_script(tmpdir, bash):
            script = tmpdir.join('test.sh')
            script.write('echo SUCCESS\\n')
            script.chmod(0o777)
            out = bash.run_script(script)
            assert out == 'SUCCESS'
    """)
    result = testdir.runpytest()
    assert result.ret == 0


def test_script_error(testdir, tmpdir):
    testdir.makepyfile("""
        def test_script_error(tmpdir, bash):
            script = tmpdir.join('test.sh')
            script.write('#!/usr/bin/env bash\\n\\nblahcommand\\n')
            script.chmod(0o777)
            out = bash.run_script(script)
        """)
    result = testdir.runpytest()
    assert result.ret != 0


def test_script_return_code(tmpdir):
    script = tmpdir.join('test.sh')
    script.write('#!/bin/env bash\n\nblahcommand\n')
    script.chmod(0o777)
    with bash() as s:
        s.auto_return_code_error = False
        out = s.run_script(script)
        assert s.last_return_code == 126


def test_env_var(testdir):
    """Test setting an environment variable."""
    with bash() as s:
        s.set_env('TEST_VARIABLE', 'blahBLAH')
        assert s.envvars['TEST_VARIABLE'] == 'blahBLAH'


def test_source(tmpdir):
    """Test that sourcing a shell file loads it."""
    script = tmpdir.join('test.sh')
    script.write('#!/bin/bash\n\necho AAAAAA\n'
                 'export TEST_ANOTHER=test\ntouch /tmp/blah')
    with bash(source=['test.sh'], pwd=tmpdir.strpath) as s:
        assert s.envvars['TEST_ANOTHER'] == 'test'


def test_fixture(testdir):
    """Test the bash fixture is available."""
    testdir.makepyfile("""
        def test_fixture(bash):
            from pytest_shell.shell import ShellSession
            assert isinstance(bash, ShellSession)
    """)
    result = testdir.runpytest()
    assert result.ret == 0


def test_return_code(testdir):
    """Test that an error status fails the test by default."""
    testdir.makepyfile("""
        def test_return_code(bash):
            bash.send('/bin/false')
    """)
    result = testdir.runpytest()
    assert result.ret == 1


def test_return_code_auto_off(testdir):
    """Test the assert failure on error can be disabled and the return code
    is captured."""
    testdir.makepyfile("""
        def test_return_code(bash):
            bash.auto_return_code_error = False
            bash.send('(exit 99)')
            assert bash.last_return_code == 99
    """)
    result = testdir.runpytest()
    assert result.ret == 0


def test_context(testdir):
    """Test behaviour of environment variables when nesting shells."""
    testdir.makepyfile("""
        def test_context(bash):
            bash.set_env('BLAH', 'SOMETHING')
            with bash(envvars={'BLAH2': 'SOMETHINGELSE'}) as inner:
                assert inner.envvars['BLAH2'] == 'SOMETHINGELSE'
                assert bash.envvars['BLAH'] == 'SOMETHING'
            assert 'BLAH2' not in bash.envvars
    """)
    result = testdir.runpytest()
    assert result.ret == 0


def test_escaping(testdir):
    """Test that commands with quotes, escapes etc work correctly."""
    testdir.makepyfile(r"""
        def test_escaping(bash):
            import shlex
            strings = [r'\"', r'"\'"', r'\"\'\"\\']
            for s in strings:
                out = bash.send('echo %s' % s)
                assert out == ''.join(shlex.split(s))
    """)
    assert testdir.runpytest().ret == 0


def test_nonblocking(testdir):
    testdir.makepyfile("""
        def test_nonblocking(bash):
            # bash.send_nowait('sleep 0.5')
            bash.send_nowait('echo blah')
            bash.wait_for('blah')
    """)
    assert testdir.runpytest().ret == 0


def test_nonblocking_timeout(testdir):
    testdir.makepyfile("""
        def test_nonblocking_timeout(bash):
            from pytest_shell.connection import TimeOutError
            import pytest
            bash.send_nowait('sleep 0.5 && echo "blah"')
            with pytest.raises(TimeOutError):
                bash.wait_for('blah', timeout=0.3)
    """)
    assert testdir.runpytest().ret == 0


def test_pattern1(testdir):
    testdir.makepyfile("""
        def test_pattern1(bash):
            bash.send_nowait('echo one')
            bash.send_nowait('echo two')
            bash.send_nowait('echo three')
            bash.send_nowait('echo four')
            bash.wait_for('two')
            bash.wait_for('four')
    """)
    assert testdir.runpytest().ret == 0


def test_pattern2(testdir):
    testdir.makepyfile("""
        def test_pattern2(bash):
            bash.send_nowait('echo one')
            bash.send_nowait('echo two')
            bash.wait_for('two')
            bash.wait_for('one')
    """)
    assert testdir.runpytest().ret == 1


def test_pattern_regex1(testdir):
    testdir.makepyfile("""
        def test_pattern_regex1(bash):
            bash.send_nowait('echo one')
            bash.send_nowait('echo two')
            bash.wait_for('^two$')
    """)
    assert testdir.runpytest().ret == 0


def test_pattern_regex2(testdir):
    testdir.makepyfile("""
        def test_pattern_regex2(bash):
            bash.send_nowait('echo one')
            bash.wait_for('^ne', timeout=0.3)
    """)
    assert testdir.runpytest().ret == 1


def test_command(testdir):
    testdir.makepyfile("""
        def test_cat():
            from pytest_shell.shell import LocalBashSession
            sh = LocalBashSession(cmd='/bin/bash')
            with sh:
                sh.send_nowait('echo blah')
                sh.wait_for('blah')
    """)
    assert testdir.runpytest(capture='no').ret == 0


def test_file_contents(testdir):
    testdir.makepyfile("""
        def test_file_contents():
            from pytest_shell.shell import LocalBashSession
            sh = LocalBashSession(cmd='/bin/bash')
            with sh:
                sh.send('echo blah > test.txt')
                contents = sh.file_contents('test.txt')
                assert contents == 'blah'
    """)
    assert testdir.runpytest(capture='no').ret == 0


def test_path_exists(testdir):
    testdir.makepyfile("""
        def test_path_exists():
            from pytest_shell.shell import LocalBashSession
            sh = LocalBashSession(cmd='/bin/bash')
            with sh:
                sh.send('touch blah.txt')
                assert sh.path_exists('blah.txt')
                assert not sh.path_exists('shouldntexist.txt')
    """)
    assert testdir.runpytest(capture='no').ret == 0


def test_subshell(testdir):
    testdir.makepyfile("""
        def test_subshell(bash):
            with bash as b:
                with b as c:
                    b.send('test')
                    assert not b.path_exists('/shouldntexist.txt')
    """)
