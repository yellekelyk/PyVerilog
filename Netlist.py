import Module
import PortIn
import PortOut
import PortClk
import ConfigParser
from ordereddict import OrderedDict
import os
import yaml
from lib.Utils.myutils import *
import re
import verilogParse

class Netlist:
    "A Verilog Netlist"

    def __init__(self):
        self.__mods = dict()
        self.__topMod = None
        self.__yaml = dict()

    mods = property(lambda self: self.__mods)
    yaml = property(lambda self: self.__yaml)
    topMod = property(lambda self: self.__topMod)

    def link(self, topModule):
        " link the design together"
        if topModule not in self.__mods:
            raise Exception(str("link error, " + topModule + 
                                " has not been defined"))

        mod = self.__mods[topModule]

        missing = set()
        # check all cells
        for cell in mod.cells:
            if mod.cells[cell].submodname not in self.__mods:
                missing.add(mod.cells[cell].submodname)

        if len(missing) > 0:
            raise Exception(str("link error, " +  
                                str(missing) + 
                                " have not been defined"))

        for cell in mod.cells:
            #if mod.cells[cell].submodname not in self.__mods:
            #    raise Exception(str("link error, " +  
            #                        mod.cells[cell].submodname +
            #                        " has not been defined"))
            
            submod = self.__mods[mod.cells[cell].submodname]
            mod.cells[cell].linkMod(submod)
            for pin in mod.cells[cell].pins:
                if pin not in submod.ports:
                    raise Exception(str("port " + pin + " not in " 
                                        + submod.name))
                mod.cells[cell].pins[pin].connectPort(submod.ports[pin])
                net =  mod.cells[cell].pins[pin].net
                if submod.ports[pin].direction == "in":
                    net.addFanout(mod.cells[cell].pins[pin])
                else:
                    net.setFanin(mod.cells[cell].pins[pin])
                
        self.__topMod = topModule


    def checkDesign(self):
        "verify the design has legal connections (post-linking)"
        
        # make sure input ports ONLY connect to input ports


        # make sure the output ports ONLY connect to output ports


        # make sure all connections have 1 and only 1 driver

        
        # sanity check all connection widths
        pass


#    def segmentDesign(self):
#        "segment the design into combinational blocks"
#        pass
#    
#
#    def findDFS(self):
#        " do a DFS search of the modules"
#        T = OrderedDict()
#        visited = OrderedDict()
#        df = OrderedDict()
#
#        # initialize all visited as False
#        cells = self.mods[self.topMod].cells
#        for cell in cells:
#            visited[cells[cell]] = False
#
#        c = len(cells)
#        dfsArgs = {'T': T, 'visited': visited, 'c': c, 'df' : df}
#        dfsArgs = self.__findDFS__(dfsArgs, visited.keys()[0])
#        return dfsArgs['df']
#
#    def __findDFS__(self, dfsArgs, cell):
#        c = dfsArgs['c']
#
#        dfsArgs['visited'][cell] = True
#        
#        print "Looking at cell " + cell.name
#        
#        for pinstr in cell.pins:
#
#            print "looking at pin " + pinstr
#
#            pin = cell.pins[pinstr]
#            # look through all successor nodes
#            if pin.port.direction == "out":
#                for inpin in pin.net.fanout:
#                    print "fans out to " + inpin.name
#                    if not dfsArgs['visited'][inpin.cell]:
#                        dfsArgs['T'][(cell, inpin.cell)] = True
#                        self.__findDFS__(dfsArgs, inpin.cell)
#
#        dfsArgs['df'][cell] = c
#        dfsArgs['c'] = c-1
#        return dfsArgs

    def addModule(self, mod):
        modname = mod.name
        if modname in self.__mods:
            print "Warning: " + modname + " has been multiply defined"
        self.__mods[modname] = mod

    def readVerilog(self, verilogFile):
        """ Parse a Gate-level Verilog file using Python"""
        mod = verilogParse.parseFile(verilogFile)
        self.__mods[mod.name] = mod


    def readYAML(self, yamlFile):
        " Read a YAML config file, build a netlist"

        file = open(yamlFile)
        nl = yaml.safe_load(file)
        file.close()
        
        # save the config info in case we need it later
        self.__yaml.update(nl)

        for modname in nl.keys():
            mod = Module.Module({"name":modname})

            inputs = cleanget(nl.get(modname), "inputs")
            for name in inputs:
                #todo: add parsing code to determine width msb/lsb here
                width = int(inputs.get(name))
                tuples = self.__makePortTupleList__(name, width)
                for tup in tuples:
                    mod.add_port(PortIn.PortIn({"name":tup[0], 
                                                "width":tup[1], 
                                                "module":mod}))

            outputs = cleanget(nl.get(modname), "outputs")
            for name in outputs:
                #todo: add parsing code to determine width msb/lsb here
                width = int(outputs.get(name))
                tuples = self.__makePortTupleList__(name, width)
                for tup in tuples:
                    mod.add_port(PortOut.PortOut({"name":tup[0], 
                                                  "width":tup[1], 
                                                  "module":mod}))

            clocks = cleanget(nl.get(modname), "clocks")
            for name in clocks:
                mod.add_port(PortClk.PortClk({"name":name, "module":mod}))

            cells = cleanget(nl.get(modname), "cells")
            for name in cells:
                submodname = cells.get(name)
                mod.new_cell({"name":name, "submodname":submodname})

            conns = cleanget(nl.get(modname), "connections")
            for name in conns:
                ports = conns.get(name)
                if name in mod.ports:
                    net = mod.ports.get(name)
                else:
                    #todo: add parsing code to determine width msb/lsb here
                    net = mod.new_net({"name":name, "width":1})
                for conn in ports.split():
                    cellport = conn.split('.')
                    if len(cellport) != 2:
                        raise Exception("Bad port: " + conn)
                    cell  = mod.cells.get(cellport[0])
                    pname = cellport[1]                
                    pin = cell.new_pin({"name":pname, "portname":pname})
                    pin.connectNet(net)

            if modname in self.__mods:
                print "Warning: " + modname + " has been multiply defined"

            self.__mods[mod.name] = mod
        
    def __makePortTupleList__(self, name, width):
        tuples = []

        if width == 1:
            tuples.append((name, width))
        elif width > 1:
            for i in range(0,width):
                tuples.append((name + "[" + str(i) + "]", 1))
        else:
            raise Exception("Bad width parameter: " + width)

        return tuples



#    def readConfig(self, configFile):
#
#        "Read a configuration file (likely DEPRECATED), build a netlist"
#
#        config = ConfigParser.SafeConfigParser(None, dict_type=OrderedDict)
#        # make options case-sensitive
#        config.optionxform = str
#        config.read(configFile)
#
#        name = os.path.splitext(os.path.basename(configFile))[0]
#        
#        mod = Module.Module({"name":name})
#
#        for name in config.options("INPUTS"):
#            #todo: add parsing code to determine width msb/lsb here
#            width = int(config.get("INPUTS", name))
#            mod.new_port({"name":name, "width":width, "direction":"in"})
#
#        for name in config.options("OUTPUTS"):
#            #todo: add parsing code to determine width msb/lsb here
#            width = int(config.get("OUTPUTS", name))
#            mod.new_port({"name":name, "width":width, "direction":"out"})
#
#        for name in config.options("CELLS"):
#            submodname = config.get("CELLS", name)
#            mod.new_cell({"name":name, "submodname":submodname})
#
#        for name in config.options("CONNECTIONS"):
#            ports = config.get("CONNECTIONS", name)
#            if name in mod.ports:
#                net = mod.ports.get(name)
#            else:
#                #todo: add parsing code to determine width msb/lsb here
#                net = mod.new_net({"name":name, "width":1})
#                
#            for conn in ports.split():
#                cellport = conn.split('.')
#                if len(cellport) != 2:
#                    raise Exception("Bad port: " + conn)
#                cell  = mod.cells.get(cellport[0])
#                pname = cellport[1]                
#                pin = cell.new_pin({"name":pname, "portname":pname})
#                pin.connectNet(net)
#
#        self.__mods[mod.name] = mod
                

