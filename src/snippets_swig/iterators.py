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
