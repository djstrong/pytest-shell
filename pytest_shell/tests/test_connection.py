from pytest_shell.connection import local_bash_connection


def test_save_output():
    cn = local_bash_connection()
    cn.start()
    cn.send('ls -alh /')
    assert len(cn.output) > 0


def test_save_stderr():
    cn = local_bash_connection()
    cn.start()
    cn.send('echo BLAAH 1>&2')
    assert len(cn.output) == 1
    assert list(cn.output.values())[0] == 'BLAAH'


def test_last_stderr():
    cn = local_bash_connection()
    cn.start()
    cn.send('echo BLAAH 1>&2')
    assert cn.last_stderr == 'BLAAH'
    cn.send('echo ZZZ 1>&2')
    assert cn.last_stderr == 'ZZZ'

