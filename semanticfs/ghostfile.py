import os

from intervaltree import Interval, IntervalTree


class GhostFile:

    def __init__(self, datapath):
        self.__data_path = datapath

        try:
            self.__filesize = os.path.getsize(datapath)
        except FileNotFoundError:
            self.__filesize = 0

        self.__rewritten_intervals = IntervalTree([Interval(0, self.__filesize)] if self.__filesize > 0 else None)

        self.__data_path_reader = open(self.__data_path, 'rb')

    def truncate(self, length):
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

        :param length:
        """
        if length > 0:
            self.__rewritten_intervals.slice(length)
            self.__rewritten_intervals = IntervalTree(self.__rewritten_intervals[0:length])
        else:
            self.__rewritten_intervals = IntervalTree()

        self.__filesize = length

        assert self.__filesize >= self.__rewritten_intervals.end()

    def write(self, buf, offset, fh):
        # FIXME Controllare bene se la copy-on-change funziona...
        # cp /x _sem/_t1/x  ->  x è anche in _sem/x? [ok]
        # cp _sem/x _sem/_t1/x (con x non già esistente)  ->  nessuna scrittura viene eseguita? [ok]
        # cp _sem/x _sem/_t1/x (con x già esistente e stesso file)  ->  nessuna scrittura viene eseguita? ERRORE: File corrotto
        # cp _sem/y _sem/_t1/x  ->  viene eseguita la scrittura correttamente?
        if offset + len(buf) <= os.path.getsize(self.__data_path) and self._is_same_data(buf, offset):
            # Ok, we don't write anything. We just remember about it.
            GhostFile._optimized_add_to_intervaltree(self.__rewritten_intervals, offset, offset + len(buf))
            self.__filesize = max(self.__filesize, offset + len(buf))

            assert self.__filesize == self.__rewritten_intervals.end()
            return len(buf)

        else:
            # TODO Do only the write if in the tree there is one contiguous interval from 0 to filesize, because it
            #      means that the previous write was real too

            # Add this write to the intervaltree so that we don't waste time filling it with zeros.
            # We're going to reset the tree anyway.
            GhostFile._optimized_add_to_intervaltree(self.__rewritten_intervals, offset, offset + len(buf))
            self.__filesize = max(self.__filesize, offset + len(buf))

            # Fill all the holes with zeros and write them
            self._write_tree_to_real_file(fh)

            # Write the new data
            os.lseek(fh, offset, os.SEEK_SET)
            written_bytes = 0
            while written_bytes < len(buf):
                written_bytes += os.write(fh, buf[written_bytes:])
            assert written_bytes == len(buf)

            # Update the structures
            self.__filesize = os.path.getsize(self.__data_path)
            self.__rewritten_intervals = IntervalTree([Interval(0, self.__filesize)] if self.__filesize > 0 else None)

            # TODO Remove
            print("Writing " + str(len(buf)) + " bytes")

            assert self.__filesize == self.__rewritten_intervals.end() == os.path.getsize(self.__data_path)
            return len(buf)

    def read(self, length, offset, fh):
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

    def apply(self, fh):
        # Fill all the holes with zeros and write them
        self._write_tree_to_real_file(fh)
        self.__rewritten_intervals = IntervalTree([Interval(0, self.__filesize)] if self.__filesize > 0 else None)

    def release(self):
        """
        Releases the resources used by this GhostFile. This object will no longer be valid after
        this method is called, so this should always be the last operation on this object.
        """
        self.__data_path_reader.close()

    @property
    def size(self):
        return self.__filesize

    def _is_same_data(self, buf, offset):
        self.__data_path_reader.seek(offset)
        olddata = self.__data_path_reader.read(len(buf))

        return buf == olddata

    @staticmethod
    def _optimized_add_to_intervaltree(tree, start, end):
        """
        Inserts the interval to the provided intervaltree. If the provided interval is adjacent to a previous
        interval or to a next interval, they get merged into a single interval. This method also guarantees
        that, in the end, there are no intervals overlapping within the provided range.

        :param tree:
        :param start:
        :param end:
        """
        prev_adjacent_intervals = tree[start - 1]
        next_adjacent_intervals = tree[end]

        # This should be true because we always prevent intervals from overlapping
        assert len(prev_adjacent_intervals) <= 1 and len(next_adjacent_intervals) <= 1

        prev_adjacent_interval = list(prev_adjacent_intervals)[0] if len(prev_adjacent_intervals) > 0 else None
        next_adjacent_interval = list(next_adjacent_intervals)[0] if len(next_adjacent_intervals) > 0 else None
        assert isinstance(prev_adjacent_interval, Interval) or prev_adjacent_interval is None
        assert isinstance(next_adjacent_interval, Interval) or next_adjacent_interval is None

        chop_from = start
        chop_to = end
        if prev_adjacent_interval is not None:
            chop_from = prev_adjacent_interval.begin
        if next_adjacent_interval is not None:
            chop_to = next_adjacent_interval.end

        # Chopping prevents overlapping intervals
        tree.chop(chop_from, chop_to)
        tree[chop_from:chop_to] = None

    def _write_tree_to_real_file(self, fh):
        end_prev_interval = 0

        for interval in self.__rewritten_intervals:
            zeros = b'\x00' * (interval.begin - end_prev_interval)
            written_bytes = 0
            os.lseek(fh, end_prev_interval, os.SEEK_SET)
            while written_bytes < len(zeros):
                written_bytes += os.write(fh, zeros[written_bytes:])
            assert written_bytes == len(zeros)
            end_prev_interval = interval.end

        zeros = b'\x00' * (self.__filesize - end_prev_interval)
        written_bytes = 0
        os.lseek(fh, end_prev_interval, os.SEEK_SET)
        while written_bytes < len(zeros):
            written_bytes += os.write(fh, zeros[written_bytes:])
        assert written_bytes == len(zeros)

        # TODO Find a way to avoid doing all this if nobody did a truncate since the last call to this method
        assert self.__filesize >= self.__rewritten_intervals.end()
        os.ftruncate(fh, self.__filesize)
