from Port import *

class PortOut(Port):

    def __init__(self, attrs):
        attrs["direction"] = "out"
        Port.__init__(self, attrs)

    # link the port!
    def link(self, net):
        net.setFanin(self)
        Port.link(self, net)
