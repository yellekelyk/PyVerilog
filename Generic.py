class Generic(object):
    "A generic pyNet object that holds some common code"
    def __init__(self, attrs):
        self.__attrs = attrs
        self.__name   = self.get("name")
        self.__module = self.get("module")


    def get(self, name, require=True):
        ret = None
        if name in self.__attrs:
            ret = self.__attrs[name]
        elif require:
            raise Exception(name + " not defined")
        return ret

    name   = property(lambda self: self.__name)
    module = property(lambda self: self.__module)
