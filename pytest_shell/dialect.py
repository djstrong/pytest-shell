import abc
import pipes

import six


class RawCommand(object):
    def __init__(self, cmd):
        self.cmd = cmd


class CommandContext(object):
    def __init__(self, cn, enter, exit):
        self.cn = cn
        self.enter = enter
        self.exit = exit

    def _exec(self, cmd):
        if isinstance(cmd, RawCommand):
            self.cn.send_raw(cmd.cmd)
        elif isinstance(cmd, six.string_types):
            self.cn.send(cmd)
        else:
            for c in cmd:
                self._exec(c)

    def __enter__(self):
        self._exec(self.enter)
        # TODO: probably a good idea to clear everything out but safer/better than a sleep?
        # time.sleep(2)
        # self.cn.connection.drain()
        # time.sleep(2)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._exec(self.exit)


class Dialect(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def path_exists(self, path):
        pass

    @abc.abstractmethod
    def file_contents(self, path):
        pass

    @abc.abstractproperty
    def envvars(self):
        pass

    @abc.abstractmethod
    def run_script_inline(self, lines):
        pass

    @abc.abstractmethod
    def run_script(self, path, args):
        pass

    @abc.abstractmethod
    def set_env(self, name, value):
        pass

    @abc.abstractmethod
    def source(self, fname):
        pass

    @abc.abstractmethod
    def cd(self, path):
        pass

    @abc.abstractmethod
    def return_code(self):
        pass

    @abc.abstractmethod
    def start_subshell(self):
        pass

    @abc.abstractmethod
    def exit(self):
        pass


class BashDialect(Dialect):

    @property
    def envvars(self):
        """

        .. fixme:: make this readonly or handle setting it
        :return:
        """
        out = self.connection.send('env', remember=False)
        vars = {}
        for line in out.splitlines():
            name, value = line.split('=', 1)
            vars[name] = value
        return vars

    def __init__(self, connection):
        self.connection = connection

    def path_exists(self, path):
        self.connection.send('stat %s' % path, remember=False)
        return 'No such file or directory' not in self.connection.last_stderr

    def file_contents(self, path):
        if self.path_exists(path):
            return self.connection.send('cat %s' % path, remember=False)

    def run_script_inline(self, lines):
        # TODO: join with newlines prior to sending?
        out = []
        for l in lines:
            out.append(self.connection.send(l))
        return '\n'.join(out)

    def run_script(self, path, args=None):
        cmd = ' '.join(pipes.quote(str(s)) for s in [path] + (args or []))
        return self.connection.send(cmd)

    def set_env(self, name, value):
        self.connection.send('export %s=%s' % (name, pipes.quote(value)),
                             remember=False)

    def source(self, fname):
        self.connection.send('source %s' % fname, remember=False)

    def cd(self, path):
        self.connection.send('cd %s' % pipes.quote(path))

    def return_code(self):
        rc = int(self.connection.send('echo $?', remember=False))
        return rc

    def start_subshell(self):
        self.connection.send(BashDialect.run_command(), remember=False)
        self.connection.drain()

    def exit(self):
        self.connection.send('exit')

    @classmethod
    def run_command(cls):
        return '/bin/bash'
