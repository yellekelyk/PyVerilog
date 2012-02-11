from Generic import *

class Pin(Generic):
    "Defines a Verilog Pin"
    def __init__(self, attrs):
        Generic.__init__(self, attrs)
        
        # attrs
        self.__cell     = self.get("cell")
        self.__portname = self.get("portname", False)
        self.__netname  = self.get("netname", False)
        
        # to be linked
        self.__net  = None
        self.__port = None

    cell = property(lambda self: self.__cell)
    port = property(lambda self: self.__port)
    net  = property(lambda self: self.__net)
    portname = property(lambda self: self.__portname)
    netname = property(lambda self: self.__netname)

    #link!
    def connect(self, net, port):
        self.connectPort(port)
        self.connectNet(net)

    def connectPort(self, port):
        self.__port     = port
        self.__portname = port.name

    def connectNet(self, net):
        self.__net     = net
        self.__netname = net.name
        

    
