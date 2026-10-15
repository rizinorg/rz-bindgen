class RzListIterator:
    def __init__(self, rzlist):
        self.iter = rzlist.iterator()

    def __next__(self):
        if self.iter is None:
            raise StopIteration
        data = self.iter.data()
        self.iter = self.iter.next()
        return data


class RzVectorIterator:
    def __init__(self, rzvector):
        self.rzvector = rzvector
        self.index = 0

    def __next__(self):
        if self.index >= len(self.rzvector):
            raise StopIteration
        data = self.rzvector.index_ptr(self.index)
        self.index += 1
        return data


class RzPVectorIterator:
    def __init__(self, rzpvector):
        self.rzpvector = rzpvector
        self.index = 0

    def __next__(self):
        if self.index >= len(self.rzpvector):
            raise StopIteration
        data = self.rzpvector.at(self.index)
        self.index += 1
        return data


class RzIteratorIterator:
    def __init__(self, rziterator):
        self.iter = rziterator

    def __iter__(self):
        return self

    def __next__(self):
        if self.iter is None:
            raise StopIteration
        data = self.iter.next()
        if data is None:
            # Iteration is done: hand ownership of the RzIterator to SWIG so
            # rz_iterator_free is called once the last reference is dropped.
            self.iter.thisown = True
            self.iter = None
            raise StopIteration
        return data
