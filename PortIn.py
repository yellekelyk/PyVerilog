from Port import *

class PortIn(Port):

    def __init__(self, attrs):
        attrs["direction"] = "in"
        Port.__init__(self, attrs)

    # link the port!
    def link(self, net):
        net.addFanout(self)
        Port.link(self, net)
