#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Basic IPcore model
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
Basic ipcore TLM model
"""

from nocmodel.noc_tlm_base import *

# ---------------------------
# Basic IPCore TLM model

class basic_ipcore_tlm(noc_tlm_base):
    """
    TLM model of a NoC ipcore. Its based on sending and receiving packets
    to a custom-based MyHDL generators. This class does not define any
    functionality.
    
    Attributes:
    * ipcore_ref: reference to ipcore base object
    
    Notes:
    * This model is completely behavioral.
    * See code comments to better understanding.
    """
    def __init__(self, ipcore_ref):
        noc_tlm_base.__init__(self)
        if isinstance(ipcore_ref, ipcore):
            self.ipcore_ref = ipcore_ref
            self.graph_ref = ipcore_ref.graph_ref
            self.logname = "IPCore '%s'" % ipcore_ref.name
            if ipcore_ref.name == "":
                self.logname = "IPCore '%s'" % ipcore_ref.router_ref.name
        else:
            raise TypeError("This class needs a ipcore object as constructor argument.")
        
        self.debug("constructor")
        # generic parameters

        # one-port support: get a reference to the related channel
        self.localch = self.ipcore_ref.channel_ref

        # get protocol reference
        self.protocol_ref = self.ipcore_ref.get_protocol_ref()
        
        # bidirectional port: the sender part will write data to the signal 
        # outgoing_packet. This class provides a generator thar call send() 
        # method when there is new data. 
        # for receiving data, recv() method will write
        # to the signal incoming_packet, and the ipcore must provide a generator 
        # sensible to that signal. Use the method register_generator()
        self.incoming_packet = myhdl.Signal(packet())
        self.outgoing_packet = myhdl.Signal(packet())
        
        @myhdl.instance
        def outgoing_process():
            while True:
                yield self.outgoing_packet
                retval = self.send(self.ipcore_ref, self.localch, self.outgoing_packet.val)
        
        self.generators = [outgoing_process]
        self.debugstate()

    def register_generator(self, genfunction, **kwargs):
        """
        Register a new generator for this ipcore. 
        
        Arguments:
        * genfunction: function that returns a MyHDL generator
        * kwargs: optional keyed arguments to pass to genfunction call
        
        Notes:
        * This method requires that genfunction has the following prototype:
            * my_function(din, dout, tlm_ref, <other_arguments>)
                * din is a MyHDL Signal of type packet, and is the input signal 
                  to the ipcore. Use this signal to react to input events and 
                  receive input packets.
                * dout is a MyHDL Signal of type packet, and is the output 
                  signal to the ipcore. Use this signal to send out packets to
                  local channel (and then insert into the NoC).
                * tlm_ref is a reference to this object. Normal use is to access
                  logging methods (e.g. tlm_ref.info("message") ).
                * <other_arguments> may be defined, this method use kwargs 
                  argument to pass them.
        """
        makegen = genfunction(din=self.incoming_packet, dout=self.outgoing_packet, tlm_ref=self, **kwargs)
        self.debug("register_generator( %s ) generator is %s args %s" % (repr(genfunction), repr(makegen), repr(kwargs)))
        self.generators.append(makegen)

    # Transaction - related methods
    def send(self, src, dest, packet, addattrs=None):
        """
        Assumptions: 
        * Safely ignore src and dest arguments, because this method 
          is called only by this object generators, therefore it always send 
          packets to the ipcore related channel.
        * In theory src should be self.ipcore_ref, and dest should be 
          self.localch . This may be checked for errors.
        """
        self.debug("-> send( %s , %s , %s , %s )" % (repr(src), repr(dest), repr(packet), repr(addattrs)))

        # call recv on the local channel object
        retval = self.localch.tlm.recv(self.ipcore_ref, self.localch, packet, addattrs)
        
        # something to do with the retval? Only report it.
        self.debug("-> send returns code '%s'" % repr(retval))
        return retval
    
    def recv(self, src, dest, packet, addattrs=None):
        """
        Assumptions: 
        * Safely ignore src and dest arguments, because this method 
          is called only by local channel object.
        * In theory src should be self.localch, and dest should be 
          self.ipcore_ref . This may be checked for errors.
        """
        self.debug("-> recv( %s , %s , %s , %s )" % (repr(src), repr(dest), repr(packet), repr(addattrs)))

        # update signal
        self.incoming_packet.next = packet

        self.debug("-> recv returns 'noc_tlm_errcodes.no_error'")
        return noc_tlm_errcodes.no_error
