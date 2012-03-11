#
# verilogParse.py
#
# an example of using the pyparsing module to be able to process Verilog files
# uses BNF defined at http://www.verilog.com/VerilogBNF.html
#
#    Copyright (c) 2004-2011 Paul T. McGuire.  All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# If you find this software to be useful, please make a donation to one
# of the following charities:
# - the Red Cross (http://www.redcross.org)
# - Hospice Austin (http://www.hospiceaustin.org)
#
#    DISCLAIMER:
#    THIS SOFTWARE IS PROVIDED BY PAUL T. McGUIRE ``AS IS'' AND ANY EXPRESS OR
#    IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#    MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO
#    EVENT SHALL PAUL T. McGUIRE OR CO-CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
#    INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#    BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OFUSE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
#    OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#    NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
#    EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#    For questions or inquiries regarding this license, or commercial use of
#    this software, contact the author via e-mail: ptmcg@users.sourceforge.net
#
# Todo:
#  - add pre-process pass to implement compilerDirectives (ifdef, include, etc.)
#
# Revision History:
#
#   1.0   - Initial release
#   1.0.1 - Fixed grammar errors:
#           . real declaration was incorrect
#           . tolerant of '=>' for '*>' operator
#           . tolerant of '?' as hex character
#           . proper handling of mintypmax_expr within path delays
#   1.0.2 - Performance tuning (requires pyparsing 1.3)
#   1.0.3 - Performance updates, using Regex (requires pyparsing 1.4)
#   1.0.4 - Performance updates, enable packrat parsing (requires pyparsing 1.4.2)
#   1.0.5 - Converted keyword Literals to Keywords, added more use of Group to
#           group parsed results tokens
#   1.0.6 - Added support for module header with no ports list (thanks, Thomas Dejanovic!)
#   1.0.7 - Fixed erroneous '<<' Forward definition in timCheckCond, omitting ()'s
#   1.0.8 - Re-released under MIT license
#   1.0.9 - Enhanced udpInstance to handle identifiers with leading '\' and subscripting
#   1.0.10 - Fixed change added in 1.0.9 to work for all identifiers, not just those used
#           for udpInstance.
#
import pdb
import time
import pprint
import sys


__version__ = "1.0.10"

from pyparsing import Literal, CaselessLiteral, Keyword, Word, Upcase, OneOrMore, ZeroOrMore, \
        Forward, NotAny, delimitedList, Group, Optional, Combine, alphas, nums, restOfLine, cStyleComment, \
        alphanums, printables, dblQuotedString, empty, ParseException, ParseResults, MatchFirst, oneOf, GoToColumn, \
        ParseResults,StringEnd, FollowedBy, ParserElement, And, Regex, cppStyleComment#,__version__
import pyparsing
usePackrat = True
usePsyco = False

packratOn = False
psycoOn = False

if usePackrat:
    try:
        ParserElement.enablePackrat()
    except:
        pass
    else:
        packratOn = True

# comment out this section to disable psyco function compilation
if usePsyco:
    try:
        import psyco
        psyco.full()
    except:
        print "failed to import psyco Python optimizer"
    else:
        psycoOn = True


def dumpTokens(s,l,t):
    import pprint
    pprint.pprint( t.asList() )

module = None

def parseModule(s,l,t):
    import Module
    global module
    module = Module.Module({"name": t[0]})

def parsePort(s,l,t,port):
    global module
    width=1
    idx=1
    # handle optional size declaration
    if t[1] == '[':
        width = int(t[2])-int(t[4])+1
        idx = 6
    token = t[idx]
    # handle possibly many signal declarations
    while token != ';':
        if token == 'clk' or token == 'CLK' or token == 'Clk':
            import PortClk
            if width != 1:
                raise Exception("Expect clock signal " + token + " to have width=1, not " + str(width))
            module.add_port(PortClk.PortClk({ "name":token, "module":module, "busMember":False, "bitIdx":None, "busName":None } ))
        elif token != ',':
            if width == 1:
                module.add_port(port({ "name":token, "width":width, "module":module, "busMember":False, "bitIdx":None, "busName":None }))
            else:
                # account for multi-bit ports by adding a new port for each bit
                for i in range( 0, width ):
                    module.add_port(port({ "name":token + "[" + str(i) + "]", "width": 1, "module":module, "busMember":True, "bitIdx":i, "busName":token }))
        #
        idx += 1
        token = t[idx]

def parseInput(s,l,t):
    import PortIn
    if t[0][0] != 'input':
        raise Exception("Expected input identifier")
    parsePort(s,l,t[0],PortIn.PortIn)

def parseOutput(s,l,t):
    import PortOut
    if t[0][0] != 'output':
        raise Exception("Expected output identifier")
    parsePort(s,l,t[0],PortOut.PortOut)

def parseSubmod(s,l,t):
    import Cell
    t = t[0]
    global module
    submodname = t[0]
    if t[1][0][0] == "#":
        raise Exception("This cell might have parameters? " + str(t[1][0]))
    name = t[1][0][0]
    cell = module.new_cell({ "name" : name, "submodname": submodname })
    
    for tok in t[1][1]:
        # look for pin-connections
        if tok != '(' and tok != ')':
            if len(tok) != 4:
                raise Exception("Expected this to have length 4")
            netName = tok[2][0]
            isBus = False
            if len(tok[2]) > 1:
                # account for possible bit select (eg [0])
                busName = netName
                bitIdx  = tok[2][1][1]
                netName += "[" + str( bitIdx ) + "]"
                isBus = True
            if netName in module.ports:
                net = module.ports.get(netName)
            elif netName in module.nets:
                net = module.nets.get(netName)
            else:
                if isBus:
                    net = module.new_net({ "name":netName, "width":1, "busMember":True,  "bitIdx":bitIdx, "busName":busName })
                else:
                    try:
                        net = module.new_net({ "name":netName, "width":1, "busMember":False, "bitIdx":None,   "busName":None    })
                    except:
                        print 'tok =', tok
                        print 'netName =', netName
                        print 'isBus =', isBus
                        raise
            #
            tmp = tok[0].split('.')
            if len(tmp) != 2:
                raise  Exception("Bad pin decl " + str(tmp))
            pinName = tmp[1]
            pin = cell.new_pin({"name":pinName, "portname":pinName})
            pin.connectNet(net)

verilogbnf = None
def Verilog_BNF():
    global verilogbnf

    if verilogbnf is None:

        # compiler directives
        compilerDirective = Combine( "`" + \
            oneOf("define undef ifdef else endif default_nettype "
                  "include resetall timescale unconnected_drive "
                  "nounconnected_drive celldefine endcelldefine") + \
            restOfLine ).setName("compilerDirective")

        # primitives
        semi = Literal(";")
        lpar = Literal("(")
        rpar = Literal(")")
        equals = Literal("=")

        identLead = alphas+"$_"
        identBody = alphanums+"$_"
        identifier1 = Regex( r"\.?["+identLead+"]["+identBody+"]*(\.["+identLead+"]["+identBody+"]*)*"
                            ).setName("baseIdent")
        identifier2 = Regex(r"\\\S+").setParseAction(lambda t:t[0][1:]).setName("escapedIdent")
        identifier = identifier1 | identifier2
        
        hexnums = nums + "abcdefABCDEF" + "_?"
        base = Regex("'[bBoOdDhH]").setName("base")
        basedNumber = Combine( Optional( Word(nums + "_") ) + base + Word(hexnums+"xXzZ"),
                               joinString=" ", adjacent=False ).setName("basedNumber")
        #~ number = ( basedNumber | Combine( Word( "+-"+spacedNums, spacedNums ) +
                           #~ Optional( "." + Optional( Word( spacedNums ) ) ) +
                           #~ Optional( e + Word( "+-"+spacedNums, spacedNums ) ) ).setName("numeric") )
        number = ( basedNumber | \
                   Regex(r"[+-]?[0-9_]+(\.[0-9_]*)?([Ee][+-]?[0-9_]+)?") \
                  ).setName("numeric")
        #~ decnums = nums + "_"
        #~ octnums = "01234567" + "_"
        expr = Forward().setName("expr")
        concat = Group( "{" + delimitedList( expr ) + "}" )
        multiConcat = Group("{" + expr + concat + "}").setName("multiConcat")
        funcCall = Group(identifier + "(" + Optional( delimitedList( expr ) ) + ")").setName("funcCall")

        subscrRef = Group("[" + delimitedList( expr, ":" ) + "]")
        subscrIdentifier = Group( identifier + Optional( subscrRef ) )
        #~ scalarConst = "0" | (( FollowedBy('1') + oneOf("1'b0 1'b1 1'bx 1'bX 1'B0 1'B1 1'Bx 1'BX 1") ))
        scalarConst = Regex("0|1('[Bb][01xX])?")
        mintypmaxExpr = Group( expr + ":" + expr + ":" + expr ).setName("mintypmax")
        primary = (
                  number |
                  ("(" + mintypmaxExpr + ")" ) |
                  ( "(" + Group(expr) + ")" ).setName("nestedExpr") | #.setDebug() |
                  multiConcat |
                  concat |
                  dblQuotedString |
                  funcCall |
                  subscrIdentifier
                  )

        unop  = oneOf( "+  -  !  ~  &  ~&  |  ^|  ^  ~^" ).setName("unop")
        binop = oneOf( "+  -  *  /  %  ==  !=  ===  !==  &&  "
                       "||  <  <=  >  >=  &  |  ^  ^~  >>  << ** <<< >>>" ).setName("binop")

        expr << (
                ( unop + expr ) |  # must be first!
                ( primary + "?" + expr + ":" + expr ) |
                ( primary + Optional( binop + expr ) )
                )

        lvalue = subscrIdentifier | concat

        # keywords
        if_        = Keyword("if")
        else_      = Keyword("else")
        edge       = Keyword("edge")
        posedge    = Keyword("posedge")
        negedge    = Keyword("negedge")
        specify    = Keyword("specify")
        endspecify = Keyword("endspecify")
        fork       = Keyword("fork")
        join       = Keyword("join")
        begin      = Keyword("begin")
        end        = Keyword("end")
        default    = Keyword("default")
        forever    = Keyword("forever")
        repeat     = Keyword("repeat")
        while_     = Keyword("while")
        for_       = Keyword("for")
        case       = oneOf( "case casez casex" )
        endcase    = Keyword("endcase")
        wait       = Keyword("wait")
        disable    = Keyword("disable")
        deassign   = Keyword("deassign")
        force      = Keyword("force")
        release    = Keyword("release")
        assign     = Keyword("assign")

        eventExpr = Forward()
        eventTerm = ( posedge + expr ) | ( negedge + expr ) | expr | ( "(" + eventExpr + ")" )
        eventExpr << (
            Group( delimitedList( eventTerm, "or" ) )
            )
        eventControl = Group( "@" + ( ( "(" + eventExpr + ")" ) | identifier | "*" ) ).setName("eventCtrl")

        delayArg = ( number |
                     Word(alphanums+"$_") | #identifier |
                     ( "(" + Group( delimitedList( mintypmaxExpr | expr ) ) + ")" )
                   ).setName("delayArg")#.setDebug()
        delay = Group( "#" + delayArg ).setName("delay")#.setDebug()
        delayOrEventControl = delay | eventControl

        assgnmt   = Group( lvalue + "=" + Optional( delayOrEventControl ) + expr ).setName( "assgnmt" )
        nbAssgnmt = Group(( lvalue + "<=" + Optional( delay ) + expr ) |
                     ( lvalue + "<=" + Optional( eventControl ) + expr )).setName( "nbassgnmt" )

        range = "[" + expr + ":" + expr + "]"

        paramAssgnmt = Group( identifier + "=" + expr ).setName("paramAssgnmt")
        parameterDecl = Group( "parameter" + Optional( range ) + delimitedList( paramAssgnmt ) + semi).setName("paramDecl")

        inputDecl = Group( "input" + Optional( range ) + delimitedList( identifier ) + semi ).setParseAction(parseInput)
        outputDecl = Group( "output" + Optional( range ) + delimitedList( identifier ) + semi ).setParseAction(parseOutput)
        inoutDecl = Group( "inout" + Optional( range ) + delimitedList( identifier ) + semi )

        regIdentifier = Group( identifier + Optional( "[" + expr + ":" + expr + "]" ) )
        regDecl = Group( "reg" + Optional("signed") + Optional( range ) + delimitedList( regIdentifier ) + semi ).setName("regDecl")
        timeDecl = Group( "time" + delimitedList( regIdentifier ) + semi )
        integerDecl = Group( "integer" + delimitedList( regIdentifier ) + semi )

        strength0 = oneOf("supply0  strong0  pull0  weak0  highz0")
        strength1 = oneOf("supply1  strong1  pull1  weak1  highz1")
        driveStrength = Group( "(" + ( ( strength0 + "," + strength1 ) |
                                       ( strength1 + "," + strength0 ) ) + ")" ).setName("driveStrength")
        nettype = oneOf("wire  tri  tri1  supply0  wand  triand  tri0  supply1  wor  trior  trireg")
        expandRange = Optional( oneOf("scalared vectored") ) + range
        realDecl = Group( "real" + delimitedList( identifier ) + semi )

        eventDecl = Group( "event" + delimitedList( identifier ) + semi )

        blockDecl = (
            parameterDecl |
            regDecl |
            integerDecl |
            realDecl |
            timeDecl |
            eventDecl
            )

        stmt = Forward().setName("stmt")#.setDebug()
        stmtOrNull = stmt | semi
        caseItem = ( delimitedList( expr ) + ":" + stmtOrNull ) | \
                   ( default + Optional(":") + stmtOrNull )
        stmt << Group(
            ( begin + Group( ZeroOrMore( stmt ) ) + end ).setName("begin-end") |
            ( if_ + Group("(" + expr + ")") + stmtOrNull + Optional( else_ + stmtOrNull ) ).setName("if") |
            ( delayOrEventControl + stmtOrNull ) |
            ( case + "(" + expr + ")" + OneOrMore( caseItem ) + endcase ) |
            ( forever + stmt ) |
            ( repeat + "(" + expr + ")" + stmt ) |
            ( while_ + "(" + expr + ")" + stmt ) |
            ( for_ + "(" + assgnmt + semi + Group( expr ) + semi + assgnmt + ")" + stmt ) |
            ( fork + ZeroOrMore( stmt ) + join ) |
            ( fork + ":" + identifier + ZeroOrMore( blockDecl ) + ZeroOrMore( stmt ) + end ) |
            ( wait + "(" + expr + ")" + stmtOrNull ) |
            ( "->" + identifier + semi ) |
            ( disable + identifier + semi ) |
            ( assign + assgnmt + semi ) |
            ( deassign + lvalue + semi ) |
            ( force + assgnmt + semi ) |
            ( release + lvalue + semi ) |
            ( begin + ":" + identifier + ZeroOrMore( blockDecl ) + ZeroOrMore( stmt ) + end ).setName("begin:label-end") |
            # these  *have* to go at the end of the list!!!
            ( assgnmt + semi ) |
            ( nbAssgnmt + semi ) |
            ( Combine( Optional("$") + identifier ) + Optional( "(" + delimitedList(expr|empty) + ")" ) + semi )
            ).setName("stmtBody")
        """
        x::=<blocking_assignment> ;
        x||= <non_blocking_assignment> ;
        x||= if ( <expression> ) <statement_or_null>
        x||= if ( <expression> ) <statement_or_null> else <statement_or_null>
        x||= case ( <expression> ) <case_item>+ endcase
        x||= casez ( <expression> ) <case_item>+ endcase
        x||= casex ( <expression> ) <case_item>+ endcase
        x||= forever <statement>
        x||= repeat ( <expression> ) <statement>
        x||= while ( <expression> ) <statement>
        x||= for ( <assignment> ; <expression> ; <assignment> ) <statement>
        x||= <delay_or_event_control> <statement_or_null>
        x||= wait ( <expression> ) <statement_or_null>
        x||= -> <name_of_event> ;
        x||= <seq_block>
        x||= <par_block>
        x||= <task_enable>
        x||= <system_task_enable>
        x||= disable <name_of_task> ;
        x||= disable <name_of_block> ;
        x||= assign <assignment> ;
        x||= deassign <lvalue> ;
        x||= force <assignment> ;
        x||= release <lvalue> ;
        """
        alwaysStmt = Group( "always" + Optional(eventControl) + stmt ).setName("alwaysStmt")
        initialStmt = Group( "initial" + stmt ).setName("initialStmt")

        chargeStrength = Group( "(" + oneOf( "small medium large" ) + ")" ).setName("chargeStrength")

        continuousAssign = Group(
            assign + Optional( driveStrength ) + Optional( delay ) + delimitedList( assgnmt ) + semi
            ).setName("continuousAssign")


        tfDecl = (
            parameterDecl |
            inputDecl |
            outputDecl |
            inoutDecl |
            regDecl |
            timeDecl |
            integerDecl |
            realDecl
            )

        functionDecl = Group(
            "function" + Optional( range | "integer" | "real" ) + identifier + semi +
            Group( OneOrMore( tfDecl ) ) +
            Group( ZeroOrMore( stmt ) ) +
            "endfunction"
            )

        inputOutput = oneOf("input output")
        netDecl1Arg = ( nettype +
            Optional( expandRange ) +
            Optional( delay ) +
            Group( delimitedList( identifier ) ) )
        #Group( delimitedList( ~inputOutput + identifier ) ) )
        netDecl2Arg = ( "trireg" +
                        Optional( chargeStrength ) +
                        Optional( expandRange ) +
                        Optional( delay ) +
                        Group( delimitedList( identifier ) ) )
        #    Group( delimitedList( ~inputOutput + identifier ) ) )
        netDecl3Arg = ( nettype +
            Optional( driveStrength ) +
            Optional( expandRange ) +
            Optional( delay ) +
            Group( delimitedList( assgnmt ) ) )
        netDecl1 = Group(netDecl1Arg + semi)
        netDecl2 = Group(netDecl2Arg + semi)
        netDecl3 = Group(netDecl3Arg + semi)

        gateType = oneOf("and  nand  or  nor xor  xnor buf  bufif0 bufif1 "
                         "not  notif0 notif1  pulldown pullup nmos  rnmos "
                         "pmos rpmos cmos rcmos   tran rtran  tranif0  "
                         "rtranif0  tranif1 rtranif1"  )
        gateInstance = Optional( Group( identifier + Optional( range ) ) ) + \
                        "(" + Group( delimitedList( expr ) ) + ")"
        gateDecl = Group( gateType +
            Optional( driveStrength ) +
            Optional( delay ) +
            delimitedList( gateInstance) +
            semi )

        udpInstance = Group( Group( identifier + Optional(range | subscrRef) ) +
            "(" + Group( delimitedList( expr ) ) + ")" )
        udpInstantiation = Group( identifier -
            Optional( driveStrength ) +
            Optional( delay ) +
            delimitedList( udpInstance ) +
            semi ).setName("udpInstantiation")#.setParseAction(dumpTokens).setDebug()

        parameterValueAssignment = Group( Literal("#") + "(" + Group( delimitedList( expr ) ) + ")" )
        namedPortConnection = Group( "." + identifier + "(" + expr + ")" )
        modulePortConnection = expr | empty
        #~ moduleInstance = Group( Group ( identifier + Optional(range) ) +
            #~ ( delimitedList( modulePortConnection ) |
              #~ delimitedList( namedPortConnection ) ) )
        inst_args = Group( "(" + (delimitedList( modulePortConnection ) |
                    delimitedList( namedPortConnection )) + ")").setName("inst_args")#.setDebug()
        moduleInstance = Group( Group ( identifier + Optional(range) ) + inst_args )

        moduleInstantiation = Group( identifier +
            Optional( parameterValueAssignment ) +
            delimitedList( moduleInstance ).setName("moduleInstanceList") +
            semi ).setName("moduleInstantiation").setParseAction(parseSubmod)

        parameterOverride = Group( "defparam" + delimitedList( paramAssgnmt ) + semi )
        task = Group( "task" + identifier + semi +
            ZeroOrMore( tfDecl ) +
            stmtOrNull +
            "endtask" )

        specparamDecl = Group( "specparam" + delimitedList( paramAssgnmt ) + semi )

        pathDescr1 = Group( "(" + subscrIdentifier + "=>" + subscrIdentifier + ")" )
        pathDescr2 = Group( "(" + Group( delimitedList( subscrIdentifier ) ) + "*>" +
                                  Group( delimitedList( subscrIdentifier ) ) + ")" )
        pathDescr3 = Group( "(" + Group( delimitedList( subscrIdentifier ) ) + "=>" +
                                  Group( delimitedList( subscrIdentifier ) ) + ")" )
        pathDelayValue = Group( ( "(" + Group( delimitedList( mintypmaxExpr | expr ) ) + ")" ) |
                                 mintypmaxExpr |
                                 expr )
        pathDecl = Group( ( pathDescr1 | pathDescr2 | pathDescr3 ) + "=" + pathDelayValue + semi ).setName("pathDecl")

        portConditionExpr = Forward()
        portConditionTerm = Optional(unop) + subscrIdentifier
        portConditionExpr << portConditionTerm + Optional( binop + portConditionExpr )
        polarityOp = oneOf("+ -")
        levelSensitivePathDecl1 = Group(
            if_ + Group("(" + portConditionExpr + ")") +
            subscrIdentifier + Optional( polarityOp ) + "=>" + subscrIdentifier + "=" +
            pathDelayValue +
            semi )
        levelSensitivePathDecl2 = Group(
            if_ + Group("(" + portConditionExpr + ")") +
            lpar + Group( delimitedList( subscrIdentifier ) ) + Optional( polarityOp ) + "*>" +
                Group( delimitedList( subscrIdentifier ) ) + rpar + "=" +
            pathDelayValue +
            semi )
        levelSensitivePathDecl = levelSensitivePathDecl1 | levelSensitivePathDecl2

        edgeIdentifier = posedge | negedge
        edgeSensitivePathDecl1 = Group(
            Optional( if_ + Group("(" + expr + ")") ) +
            lpar + Optional( edgeIdentifier ) +
            subscrIdentifier + "=>" +
            lpar + subscrIdentifier + Optional( polarityOp ) + ":" + expr + rpar + rpar +
            "=" +
            pathDelayValue +
            semi )
        edgeSensitivePathDecl2 = Group(
            Optional( if_ + Group("(" + expr + ")") ) +
            lpar + Optional( edgeIdentifier ) +
            subscrIdentifier + "*>" +
            lpar + delimitedList( subscrIdentifier ) + Optional( polarityOp ) + ":" + expr + rpar + rpar +
            "=" +
            pathDelayValue +
            semi )
        edgeSensitivePathDecl = edgeSensitivePathDecl1 | edgeSensitivePathDecl2

        edgeDescr = oneOf("01 10 0x x1 1x x0").setName("edgeDescr")

        timCheckEventControl = Group( posedge | negedge | (edge + "[" + delimitedList( edgeDescr ) + "]" ))
        timCheckCond = Forward()
        timCondBinop = oneOf("== === != !==")
        timCheckCondTerm = ( expr + timCondBinop + scalarConst ) | ( Optional("~") + expr )
        timCheckCond << ( ( "(" + timCheckCond + ")" ) | timCheckCondTerm )
        timCheckEvent = Group( Optional( timCheckEventControl ) +
                                subscrIdentifier +
                                Optional( "&&&" + timCheckCond ) )
        timCheckLimit = expr
        controlledTimingCheckEvent = Group( timCheckEventControl + subscrIdentifier +
                                            Optional( "&&&" + timCheckCond ) )
        notifyRegister = identifier

        systemTimingCheck1 = Group( "$setup" +
            lpar + timCheckEvent + "," + timCheckEvent + "," + timCheckLimit +
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck2 = Group( "$hold" +
            lpar + timCheckEvent + "," + timCheckEvent + "," + timCheckLimit +
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck3 = Group( "$period" +
            lpar + controlledTimingCheckEvent + "," + timCheckLimit +
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck4 = Group( "$width" +
            lpar + controlledTimingCheckEvent + "," + timCheckLimit +
            Optional( "," + expr + "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck5 = Group( "$skew" +
            lpar + timCheckEvent + "," + timCheckEvent + "," + timCheckLimit +
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck6 = Group( "$recovery" +
            lpar + controlledTimingCheckEvent + "," + timCheckEvent + "," + timCheckLimit +
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck7 = Group( "$setuphold" +
            lpar + timCheckEvent + "," + timCheckEvent + "," + timCheckLimit + "," + timCheckLimit +
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck = (FollowedBy('$') + ( systemTimingCheck1 | systemTimingCheck2 | systemTimingCheck3 |
            systemTimingCheck4 | systemTimingCheck5 | systemTimingCheck6 | systemTimingCheck7 )).setName("systemTimingCheck")
        sdpd = if_ + Group("(" + expr + ")") + \
            ( pathDescr1 | pathDescr2 ) + "=" + pathDelayValue + semi

        specifyItem = ~Keyword("endspecify") +(
            specparamDecl |
            pathDecl |
            levelSensitivePathDecl |
            edgeSensitivePathDecl |
            systemTimingCheck |
            sdpd
            )
        """
        x::= <specparam_declaration>
        x||= <path_declaration>
        x||= <level_sensitive_path_declaration>
        x||= <edge_sensitive_path_declaration>
        x||= <system_timing_check>
        x||= <sdpd>
        """
        specifyBlock = Group( "specify" + ZeroOrMore( specifyItem ) + "endspecify" )

        moduleItem = ~Keyword("endmodule") + (
            parameterDecl |
            inputDecl |
            outputDecl |
            inoutDecl |
            regDecl |
            netDecl3 |
            netDecl1 |
            netDecl2 |
            timeDecl |
            integerDecl |
            realDecl |
            eventDecl |
            gateDecl |
            parameterOverride |
            continuousAssign |
            specifyBlock |
            initialStmt |
            alwaysStmt |
            task |
            functionDecl |
            # these have to be at the end - they start with identifiers
            moduleInstantiation |
            udpInstantiation
            )
        """  All possible moduleItems, from Verilog grammar spec
        x::= <parameter_declaration>
        x||= <input_declaration>
        x||= <output_declaration>
        x||= <inout_declaration>
        ?||= <net_declaration>  (spec does not seem consistent for this item)
        x||= <reg_declaration>
        x||= <time_declaration>
        x||= <integer_declaration>
        x||= <real_declaration>
        x||= <event_declaration>
        x||= <gate_declaration>
        x||= <UDP_instantiation>
        x||= <module_instantiation>
        x||= <parameter_override>
        x||= <continuous_assign>
        x||= <specify_block>
        x||= <initial_statement>
        x||= <always_statement>
        x||= <task>
        x||= <function>
        """
        portRef = subscrIdentifier
        portExpr = portRef | Group( "{" + delimitedList( portRef ) + "}" )
        port = portExpr | Group( ( "." + identifier + "(" + portExpr + ")" ) )

        moduleHdr = Group ( oneOf("module macromodule") + identifier("moduleName").setParseAction(parseModule) +
                 Optional( "(" + Group( Optional( delimitedList( 
                                    Group(oneOf("input output") + 
                                            (netDecl1Arg | netDecl2Arg | netDecl3Arg) ) |
                                    port ) ) ) + 
                            ")" ) + semi ).setName("moduleHdr")

        module = Group(  moduleHdr +
                 Group( ZeroOrMore( moduleItem ) ) +
                 "endmodule" ).setName("module")#.setDebug()

        udpDecl = outputDecl | inputDecl | regDecl
        #~ udpInitVal = oneOf("1'b0 1'b1 1'bx 1'bX 1'B0 1'B1 1'Bx 1'BX 1 0 x X")
        udpInitVal = (Regex("1'[bB][01xX]") | Regex("[01xX]")).setName("udpInitVal")
        udpInitialStmt = Group( "initial" +
            identifier + "=" + udpInitVal + semi ).setName("udpInitialStmt")

        levelSymbol = oneOf("0   1   x   X   ?   b   B")
        levelInputList = Group( OneOrMore( levelSymbol ).setName("levelInpList") )
        outputSymbol = oneOf("0   1   x   X")
        combEntry = Group( levelInputList + ":" + outputSymbol + semi )
        edgeSymbol = oneOf("r   R   f   F   p   P   n   N   *")
        edge = Group( "(" + levelSymbol + levelSymbol + ")" ) | \
               Group( edgeSymbol )
        edgeInputList = Group( ZeroOrMore( levelSymbol ) + edge + ZeroOrMore( levelSymbol ) )
        inputList = levelInputList | edgeInputList
        seqEntry = Group( inputList + ":" + levelSymbol + ":" + ( outputSymbol | "-" ) + semi ).setName("seqEntry")
        udpTableDefn = Group( "table" +
            OneOrMore( combEntry | seqEntry ) +
            "endtable" ).setName("table")

        """
        <UDP>
        ::= primitive <name_of_UDP> ( <name_of_variable> <,<name_of_variable>>* ) ;
                <UDP_declaration>+
                <UDP_initial_statement>?
                <table_definition>
                endprimitive
        """
        udp = Group( "primitive" + identifier +
            "(" + Group( delimitedList( identifier ) ) + ")" + semi +
            OneOrMore( udpDecl ) +
            Optional( udpInitialStmt ) +
            udpTableDefn +
            "endprimitive" )

        verilogbnf = OneOrMore( module | udp ) + StringEnd()

        verilogbnf.ignore( cppStyleComment )
        verilogbnf.ignore( compilerDirective )

    return verilogbnf 


def test( strng ):
    tokens = []
    try:
        tokens = Verilog_BNF().parseString( strng )
    except ParseException, err:
        print err.line
        print " "*(err.column-1) + "^"
        print err
    return tokens


def parseFile(fileName):
    tokens = []
    try:
        tokens = Verilog_BNF().parseFile( fileName )
    except ParseException, err:
        print err.line
        print " "*(err.column-1) + "^"
        print err

    #tokens = []
    #numlines = 0
    #totalTime = 0
    #infile = file(fileName)
    #filelines = infile.readlines()
    #infile.close()
    #print fileName, len(filelines),
    #numlines += len(filelines)
    #teststr = "".join(filelines)
    #time1 = time.clock()
    #tokens = test( teststr )
    #time2 = time.clock()
    #elapsed = time2-time1
    #totalTime += elapsed
    #if ( len( tokens ) ):
    #    print "OK", elapsed
    return module

#~ if __name__ == "__main__":
#if 0:
#    import pprint
#    toptest = """
#        module TOP( in, out );
#        input [7:0] in;
#        output [5:0] out;
#        COUNT_BITS8 count_bits( .IN( in ), .C( out ) );
#        endmodule"""
#    pprint.pprint( test(toptest).asList() )
#
#else:
#    def main():
#        print "Verilog parser test (V %s)" % __version__
#        print " - using pyparsing version", pyparsing.__version__
#        print " - using Python version", sys.version
#        if packratOn: print " - using packrat parsing"
#        if psycoOn: print " - using psyco runtime optimization"
#        print
#
#        import os
#        import gc
#
#        failCount = 0
#        Verilog_BNF()
#        numlines = 0
#        startTime = time.clock()
#        fileDir = "."
#        #~ fileDir = "verilog/new"
#        #~ fileDir = "verilog/new2"
#        #~ fileDir = "verilog/new3"
#        allFiles = filter( lambda f : f.endswith(".v"), os.listdir(fileDir) )
#        #~ allFiles = [ "list_path_delays_test.v" ]
#        #~ allFiles = filter( lambda f : f.startswith("a") and f.endswith(".v"), os.listdir(fileDir) )
#        #~ allFiles = filter( lambda f : f.startswith("c") and f.endswith(".v"), os.listdir(fileDir) )
#        #~ allFiles = [ "ff.v" ]
#
#        pp = pprint.PrettyPrinter( indent=2 )
#        totalTime = 0
#        for vfile in allFiles:
#            gc.collect()
#            fnam = fileDir + "/"+vfile
#            infile = file(fnam)
#            filelines = infile.readlines()
#            infile.close()
#            print fnam, len(filelines),
#            numlines += len(filelines)
#            teststr = "".join(filelines)
#            time1 = time.clock()
#            tokens = test( teststr )
#            pdb.set_trace()
#            time2 = time.clock()
#            elapsed = time2-time1
#            totalTime += elapsed
#            if ( len( tokens ) ):
#                print "OK", elapsed
#                #~ print "tokens="
#                #~ pp.pprint( tokens.asList() )
#                #~ print
#
#                ofnam = fileDir + "/parseOutput/" + vfile + ".parsed.txt"
#                outfile = file(ofnam,"w")
#                outfile.write( teststr )
#                outfile.write("\n")
#                outfile.write("\n")
#                outfile.write(pp.pformat(tokens.asList()))
#                outfile.write("\n")
#                outfile.close()
#            else:
#                print "failed", elapsed
#                failCount += 1
#        endTime = time.clock()
#        print "Total parse time:", totalTime
#        print "Total source lines:", numlines
#        print "Average lines/sec:", ( "%.1f" % (float(numlines)/(totalTime+.05 ) ) )
#        if failCount:
#            print "FAIL - %d files failed to parse" % failCount
#        else:
#            print "SUCCESS - all files parsed"
#
#        return 0
#
#    #~ from line_profiler import LineProfiler
#    #~ from pyparsing import ParseResults
#    #~ lp = LineProfiler(ParseResults.__init__)
#
#    main()
#    
#    #~ lp.print_stats()
#    #~ import hotshot
#    #~ p = hotshot.Profile("vparse.prof",1,1)
#    #~ p.start()
#    #~ main()
#    #~ p.stop()
#    #~ p.close()
