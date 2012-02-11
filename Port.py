#from Generic import *
from Net import *

class Port(Net):

    "Defines a Verilog Module Port"
    def __init__(self, attrs):
        Net.__init__(self, attrs)

        # properties
        self.__dir = self.get("direction")

        if self.__dir != "in" and self.__dir != "out":
            raise Exception("Bad port direction")

        # to be linked later
        self.__net = None

    direction = property(lambda self: self.__dir)
    net       = property(lambda self: self.__net)

    # link the port!
    def link(self, net):
        self.__net = net
