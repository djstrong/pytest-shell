from __future__ import unicode_literals

import subprocess
import uuid
import fcntl
import os
from collections import OrderedDict
import re
import time
import locale
import logging


class TimeOutError(Exception): pass


def local_bash_connection(cmd='/bin/bash'):
    return LocalConnection(cmd, bash_command_terminator)


class LocalConnection(object):
    """Class representing a connection to a command executed using subprocess.
    """
    def __init__(self, command, terminator, encoding=None):
        """A connection to a local (subprocess) command.

        :param str command: Command to run on this connection.
        :param callable terminator: A function that takes the stdout of the 
            running command and returns a function that when called with all 
            currently read output of the command says whether the command is
            finished.

        ..todo:: This is getting a bit bash-specific.
        """
        self.command = command
        self.process = None
        self.parent_pipe = None
        self.child_pipe = None
        self.terminator = terminator
        self.output = OrderedDict()
        # FIXME: why the f are these dicts!?
        self.debug_output = OrderedDict()
        self.stderr_output = OrderedDict()
        self.last_stderr = ''
        self.encoding = encoding or locale.getpreferredencoding(False)
        self._blocking = False
        self._leftovers = {'out': '', 'err': ''}
        self.logger = logging.getLogger(__name__)

    @property
    def running(self):
        return self.process is not None

    @property
    def last(self):
        return list(self.output.values())[-1] if self.output else ''

    def start(self):
        """Set up the specified process and io handles.
        """
        p = self.process = subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0)
        # Use non-blocking io
        fcntl.fcntl(
            p.stdout.fileno(), fcntl.F_SETFL, 
            fcntl.fcntl(p.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(
            p.stderr.fileno(), fcntl.F_SETFL,
            fcntl.fcntl(p.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
        time.sleep(0.5)
        self.drain()

    def drain(self):
        try:
            os.read(self.process.stdout.fileno(), 1024)
        except OSError:
            pass
        try:
            os.read(self.process.stderr.fileno(), 1024)
        except OSError:
            pass

    def finish(self):
        """Clean up and end process."""
        self.process.stdin.write('exit\n'.encode(self.encoding))
        self.process.terminate()

    def send(self, text, remember=True, timeout=10.0):
        self._leftovers = {'out': '', 'err': ''}
        self._send(text)
        check_done, get_output = self.terminator(self.process.stdin,
                                                 self.encoding)
        out, stderr = self._read(timeout=timeout, done_func=check_done,
                                 extract_func=get_output)
        if remember:
            self.output[text] = out
        self.debug_output[text] = out
        self.stderr_output[text] = self.last_stderr = stderr
        return out

    def send_nowait(self, text, remember=True):
        self._send(text)

    def send_raw(self, text):
        cmd = text + '\n'
        self.logger.info('In raw: %s', repr(cmd))
        self.process.stdin.write(cmd.encode(self.encoding))

    def _send(self, text, add_newline=True):
        cmd = (text + '\n' if add_newline else '').encode(self.encoding)
        self.logger.info('In: %s', repr(cmd))
        self.process.stdin.write(cmd)

    def _read(self, timeout=10.0, done_func=None, extract_func=None, soft_timeout=True):
        """Read from stdin and stderr and return the result.

        :param float timeout: Maximum time to wait to read (but see soft_timeout).
        :param callable done_func: A function called on the output to know if
            we should stopr eading.
        :param callable extract_func: Optional function that takes the output,
            performs any required processing, and returns the output.
        :param bool soft_timeout: If True, the timeout is reset when data is
            read (e.g. x seconds of no data are required to timeout). If False,
            TimeOutError will be raised after timeout regardless of data
            being read.
        :raises TimeOutError:
        :return: Output as string.
        :rtype: str
        """
        out = ''
        stderr = ''
        fileno = self.process.stdout.fileno()
        fileno_stderr = self.process.stderr.fileno()
        started_at = time.time()
        reading = True
        while reading:
            read_out = self._leftovers['out']
            read_err = self._leftovers['err']
            # TODO: should probably work with bytes until the end
            try:
                r = os.read(fileno_stderr, 1024).decode(self.encoding)
                read_err += r
                stderr += r
            except OSError:
                pass
            try:
                read_out += os.read(fileno, 1024).decode(self.encoding)
            except OSError:
                pass
            self.logger.debug('Out: %s', read_out)
            if read_out or read_err:
                if soft_timeout:
                    # reset the timer
                    started_at = time.time()
                lines_out = read_out.splitlines(True)
                lines_err = read_err.splitlines(True)
                # This is pretty stupid
                lines = [('e', l) for l in lines_err] + [('s', l) for l in lines_out]
                while lines:
                    (source, line) = lines.pop(0)
                    out += line
                    self.logger.debug('Checking against %s', repr(out))
                    if done_func(out):
                        self.logger.debug('Matched with output %s (%s remaining)',
                                          out, repr(lines))
                        reading = False
                        # Keep everything after the line we matched for the
                        # next go. It would probably be nicer to know where
                        # the match happened and not worry about lines but
                        # that requires relying on the pattern being a regex.
                        # TODO: probably that
                        # this is stupid too
                        self._leftovers['out'] = ''.join([l for s, l in lines if s == 's'])
                        self._leftovers['err'] = ''.join([l for s, l in lines if s == 'e'])
                        break
            else:
                time.sleep(0.1)
            if time.time() - started_at >= timeout:
                self.logger.info('Timed out')
                # TODO: should still handle any output
                raise TimeOutError()
        finished = False
        while not finished:
            try:
                out += os.read(fileno, 1024).decode(self.encoding)
                finished = False
            except OSError:
                finished = True
            try:
                out += os.read(fileno_stderr, 1024).decode(self.encoding)
                finished = False
            except OSError:
                finished = finished and True
        if extract_func:
            out = extract_func(out)
        stderr = stderr.rstrip('\n')
        return out, stderr

    def wait_for(self, pattern_or_function, timeout=3.0):
        self.logger.debug('waiting for %s', pattern_or_function)
        if not callable(pattern_or_function):
            pattern_or_function = re.compile(pattern_or_function, re.M)
        if hasattr(pattern_or_function, 'search'):
            pattern = pattern_or_function
            pattern_or_function = (lambda data: pattern.search(data) is not None)
        r = self._read(timeout=timeout, done_func=pattern_or_function)[0]
        return r


def bash_command_terminator(outfile, encoding):
    """Helper function to work out when a command has finished and get the
    return code.

    .. todo:: This is very bash-specific, but also very low-level in terms of
         io, not sure where this logic goes yet.

    :param handle outfile: Handle to read and write from/to.
    :param str encoding: Encoding to use.
    :return (callable, callable): A function that determines when the running
        command has finished, and a second
        to determine the output and return code.
    """
    terminator = uuid.uuid4().hex + '-----' + 'TERMINATOR' + '-----'
    # Somewhat of a hack to print something out and keep the previous exit code
    outfile.write(('/bin/bash -c "echo %s && (exit $?)"\n'
                   % terminator).encode(encoding))
    return (lambda data: terminator in data, 
            lambda data: re.sub(r'\s*%s\s*' % terminator, '', data))
