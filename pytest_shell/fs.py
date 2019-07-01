import os
import shutil


def create_files(structure, root='/'):
    if isinstance(structure, dict):
        structure = [{k: v} for k, v in structure.items()]
    root = str(root)
    structure = [Node.from_dict(i) for i in structure]
    # Sort the structure so that dirs are created first, files second, and
    # alters (e.g. chmods) last, and within that smaller paths are created
    # first. This is mainly to handle sensibly altering files after they've
    # been created.
    structure = sorted(structure, key=lambda el: (el.type, len(el.path)))
    for node in structure:
        path = os.path.join(root, node.path)
        if not os.path.exists(path):
            if node.type == Node.DIR:
                os.makedirs(path)
                if node.mode:
                    os.chmod(path, node.mode)
            elif node.type == Node.ALTER:
                if node.mode:
                    os.chmod(path, node.mode)
            else:
                dir_ = os.path.dirname(path)
                if not os.path.exists(dir_):
                    os.makedirs(dir_)
                if node.copyfrom:
                    shutil.copy(node.copyfrom, path)
                elif node.content:
                    with open(path, 'wb') as f_out:
                        # TODO: anything better than hard-coding this?
                        f_out.write(node.content.encode('utf8'))
                else:
                    raise Exception('No creation instructions for %s' % path)
                if node.mode:
                    os.chmod(path, node.mode)


class Node(object):
    """Represents a filesystem path to be created or modified."""
    DIR = 0
    FILE = 1
    ALTER = 2

    def __init__(self, path, type, content=None, mode=None, copyfrom=None):
        """

        :param str path: A filesystem path.
        :param int type: One of Node.DIR, Node.FILE, or Node.ALTER.
        :param str content: If given, type should be Node.FILE, and this will be
            its content.
        :param int mode: (Octal) mode of the file or directory, e.g. 0777 or
            0644.
        :param str copyfrom: If given, type should be Node.FILE, and the content
            will be copied from this path.
        """
        if mode and not isinstance(mode, int):
            raise Exception('mode should be an int, got %s' % repr(mode))
        self.path = path
        self.type = type
        self.content = content
        self.mode = mode
        self.copyfrom = copyfrom

    @classmethod
    def from_dict(cls, item):
        if isinstance(item, str):
            return cls(path=item, type=cls.DIR)
        else:
            assert isinstance(item, dict)
            assert len(item) == 1
            path, config = list(item.items())[0]
            # Take a copy of config as we'll alter it
            config = dict(config)
            type_ = cls.ALTER
            copyfrom = None
            if 'copyfrom' in config:
                copyfrom = config.pop('copyfrom')
                type_ = cls.FILE
            content = None
            if 'content' in config:
                content = config.pop('content')
                type_ = cls.FILE
            mode = config.pop('mode', None)
            if config:
                raise Exception('Unrecognised operation: %s (left over: %s)' % (repr(item), repr(config)))
            return Node(path, type_, content, mode, copyfrom)
