import os

from intervaltree import Interval, IntervalTree


class GhostFile(object):

    def __init__(self, filepath, ghostpath):
        self.__write_path = ghostpath
        self.__filesize = os.path.getsize(filepath)
        self.__rewritten_intervals = IntervalTree()

    @property
    def write_path(self):
        return self.__write_path

    def truncate(self, path, length):
        """
        Example of some subsequent trucates:
         X: original data
         _: null bytes
         |: truncate position

         * Original file: XXXXXXXXXXXX
         * Truncate 1:    XXXXXX|
         * Truncate 2:    XXX|
         * Truncate 3:    XXX______|
         * Writes:        XXX____X_
         * Truncate 4:    |
         * Writes:        _X_X__XX
         * Truncate 5:    _X_X_|

        :param path:
        :param length:
        """
        if length > 0:
            self.__rewritten_intervals.slice(length)
            self.__rewritten_intervals = IntervalTree(self.__rewritten_intervals[0:length])
        else:
            self.__rewritten_intervals = IntervalTree()

        self.__filesize = length

    def write(self, path, buf, offset, fh):
        # merge overlapped intervals, merge adjacent intervals
        pass

    def read(self, path, length, offset, fh):
        normpath = os.path.normpath(path)
        if normpath == self.__write_path:
            if offset >= self.__filesize or length == 0:
                return b''

            data = b''

            intervals = IntervalTree(self.__rewritten_intervals[offset:offset+length])
            intervals.merge_overlaps()
            intervals.slice(offset)
            intervals.slice(offset + length)
            intervals = sorted(intervals[offset:offset+length])
            assert offset < self.__filesize
            assert intervals[0].begin >= offset and intervals[-1].end <= offset + length if len(intervals) > 0 else True

            if len(intervals) == 0:
                return b'\x00' * min(length, self.__filesize - offset)

            assert len(intervals) > 0

            # Used to fill any hole at the start of the read range
            end_prev_interval = offset

            # Read the data
            for interv in intervals:
                # Fill any hole before this interval
                data += b'\x00' * (interv.begin - end_prev_interval)

                os.lseek(fh, interv.begin, os.SEEK_SET)
                data += os.read(fh, interv.length())  # FIXME E in caso di EOF?

                end_prev_interval = interv.end

            # Fill any hole at the end of the read range
            data += b'\x00' * (offset + length - intervals[-1].end)

            if offset + length > self.__filesize:
                data = data[0:self.__filesize-offset]

            assert len(data) <= length
            assert offset + len(data) <= self.__filesize
            return data

        else:
            # Read physical file
            os.lseek(fh, offset, os.SEEK_SET)
            return os.read(fh, length)

    def close(self, path, fh):
        pass
