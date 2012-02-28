from Generic import *

class Net(Generic):
    "A Verilog net"
    def __init__(self, attrs):
        Generic.__init__(self, attrs)

        self.__width = self.get("width")
        self.__msb = self.get("msb", require=False)
        self.__lsb = self.get("lsb", require=False)
        self.__busMember = self.get("busMember")
        self.__busName = self.get("busName")
        self.__bitIdx  = self.get("bitIdx")

        if self.__width > 1:          
            if self.__msb == None or self.__lsb == None:
                print "Warning: using default msb/lsb for " + self.name
                self.__msb = self.__width-1
                self.__lsb = 0
                #raise Exception("width without msb and lsb")

        if self.__msb != None and self.__lsb != None:
            if self.__msb - self.__lsb + 1 != self.__width:
                raise Exception("inconsistent msb and lsb")


        #to be linked
        self.__fanin = None
        self.__fanout = []

    width   = property(lambda self: self.__width)
    msb     = property(lambda self: self.__msb)
    lsb     = property(lambda self: self.__lsb)
    fanin   = property(lambda self: self.__fanin)
    fanout  = property(lambda self: self.__fanout)
    bitIdx  = property(lambda self: self.__bitIdx)
    busName = property(lambda self: self.__busName)
    busMember = property(lambda self: self.__busMember)
    

    def setFanin(self, pin):
        if self.__fanin != None and self.__fanin != pin:
            raise Exception("different fanin already set on net " + self.name)
        self.__fanin = pin

    def addFanout(self, pin):
        self.__fanout.append(pin)

    
    
