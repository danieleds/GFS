import os


class PathInfo(object):
    SEMANTIC_PREFIX = '_'

    def __init__(self, path):
        self.__path = path

        components = os.path.normpath(path).split(os.sep)

        # Is it something semantic?
        if len(components) >= 1 and PathInfo.is_semantic_name(components[-1]):
            # /a/_b/_c
            last_nonsemantic_idx = next(
                (i for i, name in reversed(list(enumerate(components))) if PathInfo.is_semantic_name(name)), -1)
            self.__entrypoint = os.sep.join(components[0:last_nonsemantic_idx+2])
            self.__tags = components[last_nonsemantic_idx+2:]
            self.__file = ''

        elif len(components) >= 2 and PathInfo.is_semantic_name(components[-2]):
            # /a/_b/c
            assert not PathInfo.is_semantic_name(components[-1])
            last_nonsemantic_idx = next(
                (i for i, name in reversed(list(enumerate(components[0:-1]))) if PathInfo.is_semantic_name(name)), -1)
            self.__entrypoint = os.sep.join(components[0:last_nonsemantic_idx+2])
            self.__tags = components[last_nonsemantic_idx+2:-1]
            self.__file = components[-1]

        else:
            self.__entrypoint = ''
            self.__tags = []
            self.__file = ''

    @property
    def entrypoint(self) -> str:
        return self.__entrypoint

    @property
    def tags(self) -> list:
        return self.__tags

    @property
    def file(self) -> str:
        return self.__file

    @property
    def path(self) -> str:
        return self.__path

    @property
    def is_tag(self) -> bool:
        return self.entrypoint != '' and len(self.tags) > 0 and self.file == ''

    @property
    def is_entrypoint(self) -> bool:
        return self.entrypoint != '' and len(self.tags) == 0 and self.file == ''

    @property
    def is_tagged_file(self) -> bool:
        return self.entrypoint != '' and self.file != ''

    @staticmethod
    def is_semantic_name(name) -> bool:
        """
        Returns True if the name is a semantic name (stars with the semantic prefix)
        :param name: file name to check (not a path)
        :return:
        """
        return name.startswith(PathInfo.SEMANTIC_PREFIX)

    @classmethod
    def get_semantic_subpaths_info(cls, path) -> list:
        """

        :param path: a virtual path
        :return: [ {entrypoint: "/a/_b" (a virtual path), tags: ["_c", "_d", "_e"], file: "x" }, ... ]
        """
        info = []
        components = os.path.normpath(path).split(os.sep)
        state = 0

        for i, name in enumerate(components):

            if state == 0:
                # Searching an entry point
                if PathInfo.is_semantic_name(name):
                    info.append({'entrypoint': os.sep.join(components[0:i + 1]), 'tags': [], 'file': ''})
                    state = 1

            elif state == 1:
                # Collecting all the tags and the final file/folder (if there is one)
                if PathInfo.is_semantic_name(name):
                    info[-1]['tags'].append(name)
                else:
                    info[-1]['file'] = name
                    state = 0

        return info