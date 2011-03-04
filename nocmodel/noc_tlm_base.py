#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# NoC TLM simulation support
#   This module declares classes for Transaction Level Model simulation
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

# Transaction model:
#
# Objects in a noc model have a "tlm" member
# This "tlm" implements function send() and recv()

import networkx as nx
import myhdl
import logging

from noc_base import *

class noc_tlm_base():
    """
    Base class for NoC TLM simulator.
    
    This class add methods to a NoC object, required for the TLM model. Each 
    derived class must override the methods:
    
    * __init__() : its constructor contains the object TLM model (data 
      structures, generators, etc).
    * send() 
    * recv()
    
    Other methods are related to simulation configuration and logging support.
    """
    def __init__(self):
        self.log = logging.getLogger()
        self.logname = "BASECLASS"
        self.generators = []

    def get_generators(self):
        return self.generators
    
    # TLM main: every object must define this functions
    def send(self, src, dest, data, addattrs=None):
        """
        SEND method: this method MUST be called only by the local
        object who wants to start a transaction.
        
        This function will call the recv method in the right object.

        Arguments:
        * src: source object (or router address) that call this method, i.e. the
          object that starts the transaction.
        * dest: destination object (or router address) that receive the data in
          the transaction. This method will call dest' recv method.
        * data: data to be sent. Can be anything, but normally is an object of
          type packet.
        * addattrs: optional dictionary with additional arguments
        
        Return: Must return a number: 0 for everything OK, != 0 to show an error
            relevant to the caller, an exception in case of attribute error
        """
        self.debug("-> send( %s , %s , %s , %s )" % (repr(src), repr(dest), repr(packet), repr(addattrs)))
        return noc_tlm_errcodes.not_implemented

    def recv(self, src, dest, data, addattrs=None):
        """
        RECV method: this method MUST be called only by the send
        method of the object who started the transaction.
        
        Arguments:
        * src: source object (or router address) that call this method, i.e. the
          object that starts the transaction.
        * dest: destination object (or router address) that receive the data in
          the transaction. This method will call dest' recv method.
        * data: data to be sent. Can be anything, but normally is an object of
          type packet.
        * addattrs: optional dictionary with additional arguments
        
        @return Must return a number: 0 for everything OK, != 0 to show an error
            relevant to the caller, an exception in case of attribute error
        """
        self.debug("-> recv( %s , %s , %s , %s )" % (repr(src), repr(dest), repr(packet), repr(addattrs)))
        return noc_tlm_errcodes.not_implemented
    
    # logging methods (only use 4 levels)
    def debug(self, msg, *args, **kwargs):
        self.log.debug(msg, extra={"objname": self.logname}, *args, **kwargs)
    def info(self, msg, *args, **kwargs):
        self.log.info(msg, extra={"objname": self.logname}, *args, **kwargs)
    def warning(self, msg, *args, **kwargs):
        self.log.warning(msg, extra={"objname": self.logname}, *args, **kwargs)
    def error(self, msg, *args, **kwargs):
        self.log.error(msg, extra={"objname": self.logname}, *args, **kwargs)

    # special log
    def debugstate(self):
        self.debug(" '%s' object state: " % repr(self))
        for i in dir(self):
            # exclude hidden attributes
            if i[0] == "_":
                continue
            self.debug("     ['%s'] = %s " % (i, repr(getattr(self, i))))

class noc_tlm_simulation():
    """
    NoC TLM simulator object
    
    This class manages the MyHDL simulation on a NoC object and its logging 
    support.
    
    Attributes:
    * noc_ref: reference to NoC model to simulate
    * log_file: optional file to save the simulation log
    * log_level: optional logging level for the previous file
    * kwargs: optional attributes to add to this object
    """
    def __init__(self, noc_ref, log_file=None, log_level=logging.INFO, **kwargs):
        if isinstance(noc_ref, noc):
            self.noc_ref = noc_ref
        else:
            raise TypeError("This class needs a noc object as constructor argument.")
        # configure logging system
        # log errors to console, custom log to log_file if specified
        addmsg = ""
        self.log = logging.getLogger()
        self.log.setLevel(log_level)
        console_hdl = logging.StreamHandler()
        console_hdl.setLevel(logging.WARNING)
        class SimTimeFilter(logging.Filter):
            def filter(self, record):
                record.myhdltime = myhdl.now()
                return True
        self.log.addFilter(SimTimeFilter())
        self.noc_formatter = logging.Formatter("%(myhdltime)4d:%(levelname)-5s:%(objname)-16s - %(message)s")
        console_hdl.setFormatter(self.noc_formatter)
        self.log.addHandler(console_hdl)
        if log_file != None:
            file_hdl = logging.FileHandler(log_file, 'w')
            file_hdl.setLevel(log_level)
            file_hdl.setFormatter(self.noc_formatter)
            self.log.addHandler(file_hdl)
            addmsg = "and on file (%s) level %s" % (log_file, logging._levelNames[log_level])
        # ready to roll
        self.debug("Logging enabled! Running log on console level WARNING %s" % addmsg)

    def configure_simulation(self, max_time=None, add_generators=[]):
        """
        Configure MyHDL simulation.
        
        Arguments:
        * max_time: optional max time to simulate. None means simulation 
          without time limit.
        * add_generators: external MyHDL generators to add to the simulation
        """
        # myhdl simulation: extract all generators and prepare 
        # arguments
        for obj in self.noc_ref.all_list():
            add_generators.extend(obj.tlm.get_generators())
            if isinstance(obj, ipcore):
                add_generators.extend(obj.channel_ref.tlm.get_generators())
        # debug info
        #self.debug("configure_simulation: list of generators:")
        #for gen in add_generators:
            #self.debug("configure_simulation:   generator '%s'" % repr(gen))
        self.sim_object = myhdl.Simulation(*add_generators)
        self.sim_duration = max_time
        self.debug("configure_simulation: will run until simulation time '%d'" % max_time)

    def run(self):
        """
        Run MyHDL simulation
        """
        self.debug("Start simulation")
        self.sim_object.run(self.sim_duration)
        self.debug("End simulation")

    # custom logging methods (only use 4 levels)
    def debug(self, msg, *args, **kwargs):
        self.log.debug(msg, extra={"objname": "TopNoC"}, *args, **kwargs)
    def info(self, msg, *args, **kwargs):
        self.log.info(msg, extra={"objname": "TopNoC"}, *args, **kwargs)
    def warning(self, msg, *args, **kwargs):
        self.log.warning(msg, extra={"objname": "TopNoC"}, *args, **kwargs)
    def error(self, msg, *args, **kwargs):
        self.log.error(msg, extra={"objname": "TopNoC"}, *args, **kwargs)

    # special log filter: log individually by object name
    def configure_byobject_logging(self, basefilename="", log_level=logging.INFO):
        """
        Special log filter: log individually by object name
        
        Arguments:
        * basefilename: generated filenames will start with this string
        * log_level: optional logging level for previous files
        """
        # base filter
        class ObjFilter(logging.Filter):
            def __init__(self, basename):
                self.basename = basename
            def filter(self, record):
                if record.objname == self.basename:
                    return True
                return False
        # need a handler for each object
        for obj in self.noc_ref.all_list():
            newfilter = ObjFilter(obj.tlm.logname)
            newhandler = logging.FileHandler("%s_%s.log" % (basefilename, obj.tlm.logname), "w")
            newhandler.setLevel(log_level)
            newhandler.addFilter(newfilter)
            newhandler.setFormatter(self.noc_formatter)
            self.log.addHandler(newhandler)
        # Transactions logger
        class TransFilter(logging.Filter):
            def filter(self, record):
                if record.message.find("->") == 0:
                    return True
                return False
        newhandler = logging.FileHandler("%s_transactions.log" % basefilename, "w")
        newhandler.setLevel(log_level)
        newhandler.addFilter(TransFilter())
        newhandler.setFormatter(self.noc_formatter)
        self.log.addHandler(newhandler)
        # TopNoC will not be added to this set
        self.debug("Special logging enabled. basefilename=%s level %s" % (basefilename, logging._levelNames[log_level]))

class noc_tlm_errcodes():
    """
    Common error codes definition
    """
    no_error = 0
    full_fifo = -1
    packet_bad_data = -2
    tlm_badcall_recv = -3
    tlm_badcall_send = -4
    not_implemented = -5
