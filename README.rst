============
pytest-shell
============

A plugin for testing shell scripts and line-based processes with pytest.

You could use it to test shell scripts, or other commands that can be run
through the shell that you want to test the usage of.

Not especially feature-complete or even well-tested, but works for what I
wanted it for. If you use it please feel free to file bug reports or feature
requests.

----

This `pytest`_ plugin was generated with `Cookiecutter`_ along with
`@hackebrot`_'s `cookiecutter-pytest-plugin`_ template.


Features
--------

* Easy access to a bash shell through a pytest fixture.
* Set and check environment variables through Python code.
* Automatically fail test on nonzero return codes by default.
* Helpers for running shell scripts.
* Mostly, all the great stuff pytest gives you with a few helpers to make it
  work for bash.


Installation
------------

You can install "pytest-shell" via `pip`_ from `PyPI`_::

    $ pip install pytest-shell

Usage
-----

You can use a fixture called 'bash' to get a shell process you can interact
with.

Test a bash function::

    def test_something(bash):
        assert bash.run_function('test') == 'expected output'

Set environment variables, run a .sh file and check results::

    def test_something(bash):
        with bash(envvars={'SOMEDIR': '/home/blah'}) as s:
            s.run_script('dostuff.sh', ['arg1', 'arg2'])
            assert s.path_exists('/home/blah/newdir')
            assert s.file_contents('/home/blah/newdir/test.txt') == 'test text'

Run some inline script, check an environment variable was set::

    def test_something(bash):
        bash.run_script_inline(['touch /tmp/blah.txt', './another_script.sh'])
        assert bash.envvars.get('AVAR') == 'success'

Use context manager to set environment variables::

    def test_something(bash):
        with bash(envvars={'BLAH2': 'something'}):
            assert bash.envvars['BLAH2'] == 'something'

You can run things other than bash (ssh for example), but there aren't specific
fixtures and the communication with the process is very bash-specific.

Creating file and directory structures
--------------------------------------

pytest_shell.fs.create_files() is a helper to assemble a structure of files and
directories. It is best used with the tmpdir pytest fixture so you don't have
to clean up. It is used like so::

    structure = ['/a/directory',
                 {'/a/directory/and/a/file.txt': {'content': 'blah'}},
                 {'/a/directory/and': {'mode': 0o600}]
    create_files(structure)

which should create something like this::

    |
    + a
       \
        + directory
         \
          + and              # mode 600
           \
            + a
               \
                file.txt    # content equal to 'blah'

chroot helper
-------------

A context manager that creates a chroot environment is available through
the bash fixture::

    with bash.chroot(tmpdir):
        bash.send('mkdir /blah')

The only reason to use this is if you need to test something that relies on a
certain path structure anchored at root. It is fairly flimsy, and of course
requires sudo. The best way to use it is with the tmpdir fixture provided by
pytest as no cleanup is done.

/bin, /usr/bin, /lib and /lib64 are mounted into the chroot using a bind mount,
otherwise most things don't work. The chroot commands is called with --userspec
for the current user so the commands you run in there won't be run as root,
but nevertheless be careful and aware that the directories mounted in there are
your real system directories. There is no safety or security, it's just a
helper to test something that would be otherwise hard to test.


TODO
----

* Helpers for piping, streaming.
* Fixtures and helpers for docker and ssh.
* Support for non-bash shells.
* Shell instance in setup for e.g. basepath.


Refactoring TODO
----------------

* Make Connection class just handle bytes, move line-based stuff into an
  intermediary.
* Make pattern stuff work line-based or on multiline streams (in a more
  obvious way than just crafting the right regexes).
* Make pattern stuff work on part of line if desired, leaving the rest.

License
-------

Distributed under the terms of the `MIT`_ license, "pytest-shell" is free and
open source software

.. _`Cookiecutter`: https://github.com/audreyr/cookiecutter
.. _`@hackebrot`: https://github.com/hackebrot
.. _`MIT`: http://opensource.org/licenses/MIT
.. _`BSD-3`: http://opensource.org/licenses/BSD-3-Clause
.. _`GNU GPL v3.0`: http://www.gnu.org/licenses/gpl-3.0.txt
.. _`Apache Software License 2.0`: http://www.apache.org/licenses/LICENSE-2.0
.. _`cookiecutter-pytest-plugin`: https://github.com/pytest-dev/cookiecutter-pytest-plugin
.. _`file an issue`: https://github.com/{{cookiecutter.github_username}}/pytest-{{cookiecutter.plugin_name}}/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
