#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Basic Router model
#  * TLM model
#
# Author:  Oscar Diaz
# Version: 0.1
# Date:    03-03-2011

#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software  Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA  02111-1307  USA
#

#
# Changelog:
#
# 03-03-2011 : (OD) initial release
#

"""
Basic router TLM model
"""

from nocmodel.noc_tlm_base import *

# ---------------------------
# Router TLM model

class basic_router_tlm(noc_tlm_base):
    """
    TLM model of a NoC router. This router uses store-and-forward technique, 
    using the routing information from the router object. This model just
    forward the packet, and if the packet is in its router destination, send it
    to its ipcore. Each package that the ipcore generates is delivered 
    automátically.
    
    Attributes:
    * router_ref : base reference
    * fifo_len: max number of packets to hold in each port
    
    Notes:
    * This model is completely behavioral.
    * See code comments to better understanding.
    """
    def __init__(self, router_ref, fifo_len=4):
        noc_tlm_base.__init__(self)
        if isinstance(router_ref, router):
            self.router_ref = router_ref
            self.graph_ref = router_ref.graph_ref
            self.logname = "Router '%s'" % router_ref.name
            if router_ref.name == "":
                self.logname = "Router addr '%s'" % router_ref.address
        else:
            raise TypeError("This class needs a router object as constructor argument.")
        
        self.debug("constructor")
        
        # generic parameters
        self.fifo_len = fifo_len

        # delay parameters
        self.delay_route = 5        # delay for each routing decisition
        self.delay_outfromfifo = 2  # delay for extract packet from fifo to output port
        self.delay_ipcorebus = 1    # delay for ipcore local bus operations
        
        # router parameters (Assume rectangular coords)
        self.myaddress = router_ref.address
        self.mynodecoord = (router_ref.coord_x, router_ref.coord_y)

        # port additions: use a copy of the ports list, and add
        # fifo storage and signal events
        router_ref.update_ports_info()
        self.ports_info = router_ref.ports.copy()
        for p in self.ports_info.itervalues():
            p["fifo_in"] = []
            p["fifo_out"] = []
            p["fifo_in_event"] = myhdl.Signal(False)
            p["fifo_out_event"] = myhdl.Signal(False)

        # extract a list of all fifo event signals
        self.list_fifo_in_events = [i["fifo_in_event"] for i in self.ports_info.itervalues()]
        self.list_fifo_out_events = [i["fifo_out_event"] for i in self.ports_info.itervalues()]

        # the routing table is generated from the routes_info dict
        # key: its destination address
        # values: a list of ports where the package should send it. First element
        #    is the default option, next elements are alternate routes
        router_ref.update_routes_info()
        self.detailed_routingtable = self.router_ref.routes_info.copy()
        self.routingtable = {}
        for dest, data in self.detailed_routingtable.iteritems():
            self.routingtable[dest] = [x["next"] for x in data]
        # add route to myself
        self.routingtable[self.myaddress] = [self.myaddress]
        
        # log interesting info
        self.info(" router params: fifo_len=%d" % self.fifo_len)
        self.info(" router info: addr=%d coord=%s" % (self.myaddress, repr(self.mynodecoord)))
        self.info(" router ports: %s" % repr(self.ports_info))
        self.info(" router routing table: %s" % repr(self.routingtable))

        # myhdl generators (concurrent processes)
        self.generators = []
        
        # fifo out process
        @myhdl.instance
        def flush_fifo_out():
            while True:
                for port, data in self.ports_info.iteritems():
                    if len(data["fifo_out"]) > 0:
                        if not data["fifo_out_event"].val:
                            self.debug("flush_fifo_out CATCH fifo not empty and NO trigger! fifo has %s" % repr(data["fifo_out"]))
                        self.info("flush_fifo_out event in port %d" % port)
                        packet = data["fifo_out"].pop(0)
                        self.debug("flush_fifo_out port %d packet is %s (delay %d)" % (port, repr(packet), self.delay_outfromfifo))
                        # DELAY model: time to move from fifo to external port in destination object
                        yield myhdl.delay(self.delay_outfromfifo)
                        # try to send it
                        retval = self.send(self.router_ref, data["channel"], packet)
                        if retval == noc_tlm_errcodes.no_error:
                            # clean trigger
                            data["fifo_out_event"].next = False
                            #continue
                        else:
                            self.error("flush_fifo_out FAILED in port %d (code %d)" % (port, retval))
                            # error management: 
                            #TODO: temporally put back to fifo
                            self.info("flush_fifo_out packet went back to fifo.")
                            data["fifo_out"].append(packet)
                yield self.list_fifo_out_events
                self.debug("flush_fifo_out event hit. list %s" % repr(self.list_fifo_out_events))

        # routing loop
        @myhdl.instance
        def routing_loop():
            while True:
                # routing update: check all fifos
                for port, data in self.ports_info.iteritems():
                    while len(data["fifo_in"]) > 0:
                        if not data["fifo_in_event"].val:
                            self.debug("routing_loop CATCH fifo not empty and NO trigger! fifo has %s" % repr(data["fifo_in"]))
                        self.info("routing_loop fifo_in event in port %d" % port)
                        # data in fifo
                        packet = data["fifo_in"].pop(0)
                        data["fifo_in_event"].next = False
                        self.debug("routing_loop port %d packet %s to ipcore (delay %d)" % (port, repr(packet), self.delay_route))
                        # destination needed. extract from routing table
                        destaddr = packet["dst"]
                        self.debug("routing_loop port %d routingtable %s (dest %d)" % (port, repr(self.routingtable), destaddr))
                        nextaddr = self.routingtable[destaddr][0]
                        self.debug("routing_loop port %d to port %s (dest %d)" % (port, nextaddr, destaddr))
                        # DELAY model: time spent to make a route decisition
                        yield myhdl.delay(self.delay_route)
                        self.ports_info[nextaddr]["fifo_out"].append(packet)
                        # fifo trigger
                        if self.ports_info[nextaddr]["fifo_out_event"]:
                            self.debug("routing_loop CATCH possible miss event because port %d fifo_out_event=True", self.myaddress)
                        self.ports_info[nextaddr]["fifo_out_event"].next = True

                yield self.list_fifo_in_events
                self.debug("routing_loop event hit. list %s" % repr(self.list_fifo_in_events))

        # list of all generators
        self.generators.extend([flush_fifo_out, routing_loop])
        self.debugstate()

    # Transaction - related methods
    def send(self, src, dest, packet, addattrs=None):
        """
        This method will be called on a fifo available data event
        
        Notes: 
        * Ignore src object.
        * dest should be a channel object, but also can be a router address or
          a router object.
        """
        self.debug("-> send( %s , %s , %s , %s )" % (repr(src), repr(dest), repr(packet), repr(addattrs)))
        if isinstance(dest, int):
            # it means dest is a router address
            therouter = self.graph_ref.get_router_by_address(dest)
            if therouter == False:
                self.error("-> send: dest %s not found" % repr(dest) )
                return noc_tlm_errcodes.tlm_badcall_send
            # extract channel ref from ports_info
            thedest = self.ports_info[therouter.address]["channel"]
        elif isinstance(dest, router):
            # extract channel ref from ports_info
            thedest = self.ports_info[dest.address]["channel"]
        elif isinstance(dest, channel):
            # use it directly
            thedest = dest
        else:
            self.error("-> send: what is dest '%s'?" % repr(dest) )
            return noc_tlm_errcodes.tlm_badcall_send

        # call recv on the dest channel object
        retval = thedest.tlm.recv(self.router_ref, thedest, packet, addattrs)

        # TODO: something to do with the retval?
        self.debug("-> send returns code '%s'" % repr(retval))
        return retval
    
    def recv(self, src, dest, packet, addattrs=None):
        """
        This method will be called by channel objects connected to this router.
        
        Notes:
        * The recv method only affect the receiver FIFO sets
        * Ignore dest object.
        """
        
        self.debug("-> recv( %s , %s , %s , %s )" % (repr(src), repr(dest), repr(packet), repr(addattrs)))
        # src can be an address or a noc object.
        # convert to addresses
        if isinstance(src, int):
            thesrc = src
        elif isinstance(src, router):
            thesrc = src.address
        elif isinstance(src, channel):
            # get address from the other end. Use the endpoints to calculate
            # source router
            src_index = src.endpoints.index(self.router_ref) - 1
            theend = src.endpoints[src_index]
            if isinstance(theend, router):
                thesrc = theend.address
            elif isinstance(theend, ipcore):
                thesrc = theend.router_ref.address
            else:
                self.error("-> recv: what is endpoint '%s' in channel '%s'?" % (repr(theend), repr(src)) )
                return noc_tlm_errcodes.tlm_badcall_recv
        else:
            self.error("-> recv: what is src '%s'?" % repr(src) )
            return noc_tlm_errcodes.tlm_badcall_recv

        # thesrc becomes the port number
        # check if there is enough space on the FIFO
        if len(self.ports_info[thesrc]["fifo_in"]) == self.fifo_len:
            # full FIFO
            self.error("-> recv: full fifo. Try later.")
            return noc_tlm_errcodes.full_fifo
        # get into fifo
        self.ports_info[thesrc]["fifo_in"].append(packet)
        # trigger a new routing event
        if self.ports_info[thesrc]["fifo_in_event"].val:
            self.debug("-> recv: CATCH possible miss event because in port %d fifo_in_event=True", thesrc)
        self.ports_info[thesrc]["fifo_in_event"].next = True

        self.debug("-> recv returns 'noc_tlm_errcodes.no_error'")
        return noc_tlm_errcodes.no_error
