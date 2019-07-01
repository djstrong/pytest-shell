from pytest_shell.fs import Node


def test_node_parsing_dir():
    node = Node.from_dict('/a/path')
    assert isinstance(node, Node)
    assert node.copyfrom is None
    assert node.path == '/a/path'
    assert node.type == node.DIR


def test_node_parsing_file():
    node = Node.from_dict({'/a/file': {'content': 'blah'}})
    assert isinstance(node, Node)
    assert node.type == node.FILE
    assert node.content == 'blah'
    assert node.copyfrom is None


def test_node_parsing_copyfrom():
    node = Node.from_dict({'/a/file': {'copyfrom': '/bin/bash'}})
    assert isinstance(node, Node)
    assert node.type == Node.FILE
    assert node.copyfrom == '/bin/bash'
    assert node.content is None


def test_node_parsing_invalid():
    import pytest
    with pytest.raises(Exception):
        Node.from_dict({'/a/file': {'floppynom': '/bin/bash'}})


def test_create_structure(testdir):
    testdir.makepyfile("""
        def test_file_contents(tmpdir, bash):
            import os
            from pytest_shell.fs import create_files
            s = ['tmp/one', {'tmp/one/blah.txt': {'content': 'somecontent'}},
                 {'tmp/one/blah.txt': {'mode': int('777', base=8)}}]
            create_files(s, tmpdir)
            assert bash.path_exists(os.path.join(str(tmpdir), 'tmp/one/blah.txt'))
            assert bash.file_contents(os.path.join(str(tmpdir), 'tmp/one/blah.txt')) == 'somecontent'            
    """)
    assert testdir.runpytest(capture='no').ret == 0


def test_create_structure_copyfile(testdir):
    testdir.makepyfile("""
        def test_create_structure_copyfile(tmpdir, bash):
            import os
            from pytest_shell.fs import create_files
            s = [{'bin/bash': {'copyfrom': '/bin/bash'}}]
            create_files(s, tmpdir)
            tmpbash = '%s/bin/bash' % tmpdir
            assert os.path.exists(tmpbash)
            assert bash.send('md5sum /bin/bash').split()[0] == bash.send('md5sum %s' % tmpbash).split()[0]
    """)
    assert testdir.runpytest(capture='no').ret == 0
