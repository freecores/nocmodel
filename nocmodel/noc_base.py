#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# NoC Base Objects
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
================
NoCmodel Base Objects
================
  
This module declares classes used on a Network-on-chip representation:
  
* NoC container class
    * Router base class
    * Channel base class
    * IPCore base class
    * Protocol base class
    * Packet class
"""

import networkx as nx

class noc(nx.Graph):
    """
    Base class for NoC modeling.
    Based on a Graph object that hold the NoC structure
    
    Arguments
    * kwargs: optional parameters to put as object attributes
    """
    def __init__(self, **kwargs):
        """
        NoCmodel constructor
        """
        nx.Graph.__init__(self, **kwargs)

    # objects management functions
    def add_router(self, name="", with_ipcore=False, **kwargs):
        """
        Create a base router object and add it to NoC model.

        Arguments
        * name: optional name for this router. By default has the form of 
          "R_<index>"
        * with_ipcore: If True, add an ipcore to the created router.
        * kwargs: optional parameters to put as object attributes

        Return: reference to the created router object
        """
        #nodeidx = self._get_next_nodeidx()
        routernode = router(index=None, name=name, graph_ref=self, **kwargs)
        retval = self.add_router_from_object(routernode)
        if name == "":
            retval.name = "R_%d" % retval.index
        if with_ipcore:
            # kwargs are reserved for router creation, not for ipcore.
            self.add_ipcore(retval)
        return retval
    
    def add_router_from_object(self, router_ref):
        """
        Add an existing router object to NoC model.
        
        Use this function to add an object based on a derived class of 
        base router defined in this module.

        Arguments
        * router_ref: reference to the router object

        Return: the same reference passed in router_ref
        
        Notes: 
        * This function will change router_ref.index and router_ref.graph_ref 
          attributes when inserted in the NoC model.
        """
        if not isinstance(router_ref, router):
            raise ValueError("Argument 'router_ref' is not a router object.")

        router_ref.index = self._get_next_nodeidx()
        router_ref.graph_ref = self
        # don't forget that index is used for address
        router_ref.address = router_ref.index
        self.add_node(router_ref.index, router_ref=router_ref)
        return router_ref

    def add_channel(self, router1, router2, name="", **kwargs):
        """
        Create a base channel object to link two objects and add it 
        to NoC model.

        Arguments:
        * router1: reference to a router, router index or ipcore
        * router2: -idem-
        * name: optional argument for channel name
        * kwargs: optional parameters to put as object attributes

        Notes:
        * If router1 or router2 is an ipcore reference, this method creates
          the special channel object and update ipcore references. Additionally,
          if both arguments are ipcores, throw an error exception
        """
        if isinstance(router1, ipcore) and isinstance(router2, ipcore):
            raise ValueError("Both object references cannot be ipcore objects.")

        rhash = [None, None]
        rrefs = [None, None]
        for targetid, routertarget in enumerate((router1, router2)):
            if isinstance(routertarget, router):
                if routertarget.index in self.node:
                    rhash[targetid] = routertarget.index
                    rrefs[targetid] = self.node[routertarget.index]["router_ref"]
            elif isinstance(routertarget, ipcore):
                # special channel
                rhash[targetid] = None
                rrefs[targetid] = routertarget
            elif isinstance(routertarget, int):
                if routertarget in self.node:
                    rhash[targetid] = routertarget
                    rrefs[targetid] = self.node[routertarget]["router_ref"]

        if rrefs[0] is None:
            raise ValueError("Object not found for argument 'router1'")
        if rrefs[1] is None:
            raise ValueError("Object not found for argument 'router2'")

        if None in rhash:
            ipcore_idx = rhash.index(None)
            # ipcore channel
            if name == "":
                # channel default name format 
                name = "CH_IP_%s" % rrefs[ipcore_idx].name
            channelnode = channel(index=None, name=name, graph_ref=self, **kwargs)
        else:
            # inter-routers channel
            if name == "":
                # channel default name format 
                name = "CH_%s:%s" % (rrefs[0].name, rrefs[1].name)
            channelnode = channel(index=self._get_next_edgeidx(), name=name, graph_ref=self, **kwargs)
            self.add_edge(rhash[0], rhash[1], channel_ref = channelnode)
        channelnode.endpoints = rrefs
        return channelnode
    
    def add_from_channel(self, channel_ref, router1=None, router2=None):
        """
        Add a channel object to NoC model.
        
        Use this function to add an object based on a derived class of 
        base channel defined in this module.

        Arguments
        * channel_ref: reference to the channel object
        * router1: optional reference to a router, router index or ipcore
        * router2: -idem-
        
        Return: the same reference passed in channel_ref
        
        Notes:
        * If router1 or router2 are not used as arguments, will assume that
          channel object has defined its attribute "endpoints" with the 
          objects to connect. If the objects don't exist in the NoC model,
          throw an error exception.

        * If router1 or router2 is an ipcore reference, this method creates
          the special channel object and update ipcore references. Additionally,
          if both arguments are ipcores, throw an error exception.
            
        * This function will change channel_ref.index and channel_ref.graph_ref 
          attributes when inserted in the NoC model. Also it may change 
          channel_ref.endpoints with router1 and router2 references.
        """
        if not isinstance(channel_ref, channel):
            raise ValueError("Argument 'channel_ref' is not a channel object.")

        if isinstance(router1, ipcore) and isinstance(router2, ipcore):
            raise ValueError("Both object references cannot be ipcore objects.")

        rhash = [None, None]
        rrefs = [None, None]
        for targetid, routertarget in enumerate((router1, router2)):
            if isinstance(routertarget, router):
                if routertarget.index in self.node:
                    rhash[targetid] = routertarget.index
                    rrefs[targetid] = self.node[routertarget.index]["router_ref"]
            elif isinstance(routertarget, ipcore):
                # special channel
                rhash[targetid] = None
                rrefs[targetid] = routertarget
            elif isinstance(routertarget, int):
                if routertarget in self.node:
                    rhash[targetid] = routertarget
                    rrefs[targetid] = self.node[routertarget]["router_ref"]

        if (router1 is None) and (router2 is None):
            # extract from endpoints attribute
            if not hasattr(channel_ref, "endpoints"):
                raise ValueError("Channel object has not attribute 'endpoints'")
            for i in range(2):
                if not isinstance(channel_ref.endpoints[i], [router, ipcore]):
                    raise ValueError("Channel object: attribute 'endpoints'[%d] is not a router or an ipcore" % i)
                if isinstance(channel_ref.endpoints[i], router):
                    if channel_ref.endpoints[i].index in self.node:
                        rhash[i] = channel_ref.endpoints[i].index
                        rrefs[i] = channel_ref.endpoints[i]
                if isinstance(channel_ref.endpoints[i], ipcore):
                    rhash[i] = None
                    rrefs[i] = channel_ref.endpoints[i]

        if rrefs[0] is None:
            raise ValueError("Object not found for argument 'router1'")
        if rrefs[1] is None:
            raise ValueError("Object not found for argument 'router2'")

        if None in rhash:
            ipcore_idx = rhash.index(None)
            channel_ref.index = None
            # ipcore channel: adjust the references
            rrefs[ipcore_idx].channel_ref = channel_ref
            # the other reference must be a router object
            rrefs[ipcore_idx - 1].ipcore_ref = rrefs[ipcore_idx]
        else:
            # inter-routers channel
            channel_ref.index = self._get_next_edgeidx()
            self.add_edge(rhash[0], rhash[1], channel_ref=channel_ref)
        # update common references
        channel_ref.graph_ref = self
        channel_ref.endpoints = rrefs
        return channel_ref
        

    def add_ipcore(self, router_ref, name="", **kwargs):
        """
        Create an ipcore object and connect it to the router reference argument

        Arguments
        * router_ref: reference to an existing router
        * name: optional name for this router. By default has the form of 
          "IP_<router_index>"
        * kwargs: optional parameters to put as object attributes

        Return: reference to the created ipcore object

        Notes:
        * This function automatically adds a special channel object 
          (router-to-ipcore) and adjust its relations in all involved objects.
        """
        if router_ref not in self.router_list():
            raise ValueError("Argument 'router_ref' must be an existing router.")
        if name == "":
            # channel default name format 
            name = "IP_%d" % router_ref.index
        # fix channel name, based on ipcore name
        chname = "CH_%s" % name
        newip = ipcore(name=name, router_ref=router_ref, graph_ref=self, **kwargs)
        channelnode = channel(index=None, name=chname, graph_ref=self, endpoints=[router_ref, newip])
        # fix references
        newip.channel_ref = channelnode
        router_ref.ipcore_ref = newip
        return newip
    
    def add_from_ipcore(self, ipcore_ref, router_ref, channel_ref=None):
        """
        Add a ipcore object to NoC model.

        Arguments
        * ipcore_ref: reference to ipcore object
        * router_ref: reference to an existing router to connect
        * channel_ref: optional channel object that connect the router and
          the ipcore. If not used, this function will create a new channel object.

        Return: the same reference passed in ipcore_ref

        Notes:
        * This function automatically adds a special channel object 
          (router-to-ipcore) and adjust its relations in all involved objects.
        """
        if not isinstance(ipcore_ref, ipcore):
            raise ValueError("Argument 'ipcore_ref' is not an ipcore object.")
        if router_ref not in self.router_list():
            raise ValueError("Argument 'router_ref' must be an existing router.")

        if channel_ref != None:
            if not isinstance(channel_ref, channel):
                raise ValueError("Argument 'channel_ref' is not a channel object.")
            else:
                channel_ref.index = None
                channel_ref.graph_ref = self
                channel_ref.endpoints = [router_ref, ipcore_ref]
        else:
            # channel default name format 
            chname = "CH_IP_%d" % router_ref.index
            channel_ref = channel(index=None, name=chname, graph_ref=self, endpoints=[router_ref, ipcore_ref])
        
        # fix references
        ipcore_ref.router_ref = router_ref
        ipcore_ref.channel_ref = channel_ref
        ipcore_ref.graph_ref = self
        router_ref.ipcore_ref = ipcore_ref
        
        return ipcore_ref

    def del_router(self, router_ref):
        """
        Remove router_ref from the NoC model
        
        TODO: not implemented
        """
        pass

    def del_channel(self, channel_ref):
        """
        Remove channel_ref from the NoC model
        
        TODO: not implemented
        """
        pass
        
    def del_ipcore(self, ipcore_ref):
        """
        Remove ipcore_ref from the NoC model
        
        TODO: not implemented
        """
        pass

    # list generation functions
    def router_list(self):
        l = []
        for i in self.nodes_iter(data=True):
            l.append(i[1]["router_ref"])
        return l

    def ipcore_list(self):
        l = []
        for i in self.nodes_iter(data=True):
            if i[1]["router_ref"].ipcore_ref != None:
                l.append(i[1]["router_ref"].ipcore_ref)
        return l

    def channel_list(self):
        # this function does not list ipcore channels
        l = []
        for i in self.edges_iter(data=True):
            l.append(i[2]["channel_ref"])
        return l
        
    def all_list(self):
        l = self.router_list()
        l.extend(self.ipcore_list())
        l.extend(self.channel_list())
        return l

    # query functions
    def get_router_by_address(self, address):
        for r in self.router_list():
            if r.address == address:
                return r
        return False

    # hidden functions
    def _add_router_from_node(self, node, name="", router_ref=None, **kwargs):
        """
        Create a router object (or use an existing router reference) based on 
        an existing empty node on graph object.
        """
        if router_ref is None:
            # index comes from node
            if name == "":
                name = "R_%d" % node
            routernode = router(index=node, name=name, graph_ref=self, **kwargs)
        else:
            if not isinstance(router_ref, router):
                raise ValueError("Argument 'router_ref' is not a router object.")
            routernode = router_ref
            routernode.index = node
            routernode.graph_ref = self
        self.node[node]["router_ref"] = routernode
        return routernode

    def _add_channel_from_edge(self, edge, name="", channel_ref=None, **kwargs):
        """
        Create a channel object (or use an existing channel reference) based 
        on an existing edge on graph object.
        """
        # inter-routers channels only
        rrefs = [self.node[edge[0]]["router_ref"], self.node[edge[1]]["router_ref"]]
        chindex = self.edges().index(edge)
        if channel_ref is None:
            if name == "":
                # channel default name format 
                name = "CH_%s:%s" % (rrefs[0].name, rrefs[1].name)
            channelnode = channel(index=chindex, name=name, graph_ref=self, **kwargs)
        else:
            if not isinstance(channel_ref, channel):
                raise ValueError("Argument 'channel_ref' is not a channel object.")
            channelnode = channel_ref
            channelnode.index = chindex
            channelnode.graph_ref = self
        channelnode.endpoints = rrefs
        self.get_edge_data(edge[0], edge[1])["channel_ref"] = channelnode

        return channelnode

    def _get_next_nodeidx(self):
        # get the next node index number
        # don't use intermediate available indexes
        return len(self.nodes())

    def _get_next_edgeidx(self):
        # get the next edge index number
        # don't use intermediate available indexes
        return len(self.edges())

# *******************************
# Generic models for NoC elements
# *******************************

class nocobject():
    """
    NoC base object
    
    This base class is used to implement common methods for NoC objects.
    Don't use directly.
    """
    def get_protocol_ref(self):
        """
        Get protocol object for this instance
        """
        if hasattr(self, "protocol_ref"):
            if isinstance(self.protocol_ref, protocol):
                return self.protocol_ref
        if isinstance(self.graph_ref.protocol_ref, protocol):
            return self.graph_ref.protocol_ref
        # nothing?
        return None

class ipcore(nocobject):
    """
    IP core base object
    
    This object represents a IP Core object and its properties. This base class
    is meant to either be inherited or extended by adding other attributes.

    Relations with other objects:
    * It should be related to one NoC model object (self.graph_ref)
    * It should have one reference to a router object (self.router_ref), even if
      the ipcore has a direct connection to the NoC.
    * It should have one reference to a channel object (self.channel_ref). This
      channel exclusively link this ipcore and its router.

    Attributes:
    * name
    * router_ref: optional reference to its related router.
    * channel_ref: optional reference to its related channel
    * graph_ref: optional reference to its graph model
    """
    def __init__(self, name, **kwargs):
        # Basic properties
        self.name = name
        # default values
        self.router_ref = None
        self.channel_ref = None
        self.graph_ref = None
        for key in kwargs.keys():
            setattr(self, key, kwargs[key])

class router(nocobject):
    """
    Router base object

    This object represents a router object and its properties. This base class
    is meant to either be inherited or extended by adding other attributes.

    Relations with other objects:
    * It should be related to one NoC model object (self.graph_ref)
    * It should be one of the node attributes in the graph model 
      (node["router_ref"])
    * It may have one reference to an ipcore object (self.ipcore_ref)
    * It has a port list with relations to other routers through channel objects,
      and only one relation to its ipcore object through one channel.
      (self.ports). Note that this attribute must be updated after changing 
      the NoC model.

    Attributes:
    * index: index on a noc object. Essential to search for a router object
    * name
    * ipcore_ref: optional reference to its related ipcore
    * graph_ref: optional reference to its graph model
    """
    def __init__(self, index, name, **kwargs):
        # Basic properties
        self.index = index
        self.name = name
        # default values
        self.ipcore_ref = None
        self.graph_ref = None
        # address can be anything, but let use index by default
        # note that address can be overriden with optional arguments in kwargs
        self.address = index
        for key in kwargs.keys():
            setattr(self, key, kwargs[key])
        # ports structure
        self.ports = {}
        # available routes info
        self.routes_info = {}

    # update functions: call them when the underlying NoC structure
    # has changed
    def update_ports_info(self):
        """
        Update the dictionary "ports": information about router neighbors,
        the channels that connect them and its references.
        
        Ports dictionary has the following structure:
        * key: address of the neighbor router that this port connects.
        * value: dictionary with the following keys:
            * "peer" (required): reference to the neighbor router
            * "channel" (required): reference to the channel that connects this 
              router and its neighbor router.
            * Optional keys can be added to this dictionary.
        * Also, the special key "local address" holds the port to 
          router's ipcore. Its values are:
            * "peer" (required): reference to its ipcore
            * "channel" (required): reference to the channel that connects this 
              router and its ipcore.
            * Optional keys can be added to this dictionary with the same 
              meaning as other ports.
        """
        # port definitions
        localhash = self.address
        updated_addr = [self.address]
        for neighborhash in self.graph_ref.neighbors(localhash):
            neighbor = self.graph_ref.node[neighborhash]["router_ref"]
            #check if already defined in ports dictionary
            if neighbor.address not in self.ports:
                self.ports[neighbor.address] = {}
            # update relevant data
            self.ports[neighbor.address]["peer"] = neighbor
            ch_ref = self.graph_ref.edge[localhash][neighborhash]["channel_ref"]
            self.ports[neighbor.address]["channel"] = ch_ref
            updated_addr.append(neighbor.address)

        # special port: ipcore
        if self.address not in self.ports:
            self.ports[self.address] = {}
        self.ports[self.address]["peer"] = self.ipcore_ref
        # take channel reference from ipcore. Other channels are related to
        # an edge on the graph model. Channels in an ipcore are special because
        # they don't have a related edge, just link an ipcore and this router
        self.ports[self.address]["channel"] = self.ipcore_ref.channel_ref 

        # clean 'deleted' ports
        keys = self.ports.iterkeys()
        for deleted in keys:
            if deleted not in updated_addr:
                del self.ports[deleted]

    def update_routes_info(self):
        """
        Update the dictionary "routes_info": it is a table with information 
        about how a package, starting from this router, can reach another one.
        
        routes_info dictionary has the following structure:
        * keys : the address of all the routers in NoC
        * values : an ordered list of dictionaries with 
            * "next" : address of the next router
            * "paths" : list of possible paths for key destination
        
        """
        # this function will calculate a new table!
        self.routes_info.clear()
        
        #mynodehash = (self.coord_x, self.coord_y)
        mynodehash = self.index
        
        for destrouter in self.graph_ref.router_list():
            # discard route to myself
            if destrouter == self:
                continue
            #desthash = (destrouter.coord_x, destrouter.coord_y)
            desthash = destrouter.index

            # entry for destrouter
            self.routes_info[destrouter.index] = []

            # first: take all shortest paths (function not available on NetworkX)
            shortest_routes = all_shortest_paths(self.graph_ref, mynodehash, desthash)
            # convert nodehashes to router addresses
            shortest_r_addr = [map(lambda x : self.graph_ref.node[x]["router_ref"].address, i) for i in shortest_routes]

            # NOTE about routing tables: need to think about which routes based on 
            # shortest paths are better in general with other routers, so the links
            # are well balanced. A possible problem could be that some links will carry
            # more data flow than others.
            # A possible workaround lies in the generation of routing tables at
            # NoC level, taking account of neighbors tables and others parameters.

            # extract the next neighbor in each path
            for route in shortest_r_addr:
                # first element is myself, last element is its destination. 
                # for this routing table, we only need the next router to
                # send the package.
                newroute = True
                for route_entry in self.routes_info[destrouter.index]:
                    if route[1] == route_entry["next"]:
                        # another route which next element was taken account
                        route_entry["paths"].append(route)
                        newroute = False
                if newroute:
                    self.routes_info[destrouter.index].append({"next": route[1], "paths": [route]})
            # last option: send through another node not in the shortest paths 
            # NOTE: decide if this is needed or make sense

class channel(nocobject):
    """
    Channel base object

    This object represents a channel object and its properties. This base class
    is meant to either be inherited or extended by adding other attributes.

    Relations with other objects:
    * It should be related to one NoC model object (self.graph_ref)
    * It may be one of the edge attributes in the graph model 
      (edge["channel_ref"]). In this case, this channel connects two routers
      in the NoC model.
    * It should have two references to NoC objects (self.endpoints). Two options
      exists: two routers references (channel has an edge object) or, one
      router and one ipcore (channel don't have any edge object).

    Attributes:
    * name
    * index: optional index on a noc object. Must have an index when it has
      a related edge in the graph model (and allowing it to be able to do
      channel searching). None means it is an ipcore related channel
    * graph_ref optional reference to its graph model
    * endpoints optional two-item list with references to the connected objects
    """
    def __init__(self, name, index=None, **kwargs):
        # Basic properties
        self.index = index
        self.name = name
        # Default values
        self.graph_ref = None
        self.endpoints = [None, None]
        for key in kwargs.keys():
            setattr(self, key, kwargs[key])

    def is_ipcore_link(self):
        """
        Checks if this channel is a special link for an ipcore.
        
        Return: True if the channel is related to an ipcore
        """
        # Search for ipcore in endpoints. Don't check None on self.index.
        for ref in self.endpoints:
            if isinstance(ref, ipcore):
                return True
        return False
        
class protocol(nocobject):
    """
    Protocol base object

    This object represents the protocol that the NoC objects use. This 
    object has attributes that define the protocol used, mainly it can be
    used to generate, encode, decode or interpret packets on the NoC.
    This base class can be either be inherited or extended by adding 
    other attributes.

    Relations with other objects:
    * Each object on the NoC (routers, channels and ipcores) may have
      one reference to a protocol object (object.protocol_ref)
    * A NoC model may have a protocol object: in this case, all objects in
      the model will use this protocol (nocmodel.protocol_ref)
    * A protocol object is a generator of packet objects

    Attributes:
    * name
    
    Notes: 
    * Optional arguments "packet_format" and "packet_order" can be
      added at object construction, but will not check its data consistency. 
      At the moment, we recommend using update_packet_field() method to
      fill this data structures.
    """
    def __init__(self, name="", **kwargs):
        """
        Constructor
        
        Notes:
        * Optional arguments will be added as object attributes.
        """
        # NOTE: to avoid python version requirements (2.7), implement ordered 
        # dict with an additional list. When we are sure of using 
        # Python > 2.7 , change to collections.OrderedDict
        self.name = name
        self.packet_format = {}
        self.packet_order = []
        self.packet_class = packet
        for key in kwargs.keys():
            setattr(self, key, kwargs[key])
            
    def get_protocol_ref(self):
        # override to use myself
        return self
        
    def update_packet_field(self, name, type, bitlen, description=""):
        """
        Add or update a packet field.
        
        Arguments
        * name
        * type: string that can be "int", "fixed" or "float"
        * bitlen: bit length of this field
        * description: optional description of this field
        
        Notes: 
        * Each new field will be added at the end. 
        """
        if (type != "int") and (type != "fixed") and (type != "float"):
            raise ValueError("Argument 'type' must be 'int', 'fixed' or 'float'.")
        
        if name in self.packet_format:
            # update field
            previdx = self.packet_order.index(name) - 1
            if previdx < 0:
                # first field
                lastbitpos = 0
            else:
                lastbitpos = self.packet_format[self.packet_order[previdx]][lsb]
            nextbitpos = lastbitpos + bitlen
            self.packet_format[name]["type"] = type
            self.packet_format[name]["position"] = previdx + 1
            # check if the packet format needs to adjust the bit positions
            if self.packet_format[name]["bitlen"] != bitlen:
                self.packet_format[name]["bitlen"] = bitlen
                self.packet_format[name]["lsb"] = nextbitpos
                self.packet_format[name]["msb"] = lastbitpos
                # iterate through the rest of the fields adjusting lsb and msb
                for idx in range(previdx+2, len(self.packet_order)):
                    curname = self.packet_order[idx]
                    curbitlen = self.packet_format[curname]["bitlen"] 
                    self.packet_format[curname]["lsb"] = nextbitpos + curbitlen
                    self.packet_format[curname]["msb"] = nextbitpos
                    nextbitpos += curbitlen
        else:
            # append
            if len(self.packet_format) == 0:
                lastbitpos = 0
            else:
                lastbitpos = self.packet_format[self.packet_order[-1]]["lsb"]
            nextbitpos = lastbitpos + bitlen
            fieldpos = len(self.packet_order)
            self.packet_format[name] = {"type": type, "position": fieldpos, "bitlen": bitlen, "lsb": nextbitpos, "msb": lastbitpos}
            self.packet_order.append(name)
        
    def newpacket(self, zerodefault=True, *args, **kwargs):
        """
        Return a new packet with all required fields.
        
        Arguments:
        * zerodefault: If True, all missing fields will be zeroed by default.
          If False, a missing value in arguments will throw an exception.
        * args: Nameless arguments will add field values based on packet field
          order.
        * kwargs: Key-based arguments will add specified field values based in 
          its keys
            
        Notes: 
        * kwargs takes precedence over args: i.e. named arguments can overwrite
          nameless arguments.
        """
        retpacket = self.packet_class(protocol_ref=self)
        fieldlist = self.packet_order[:]
        # first named arguments
        for fkey, fvalue in kwargs.iteritems():
            if fkey in fieldlist:
                retpacket[fkey] = fvalue
                fieldlist.remove(fkey)
        # then nameless
        for fidx, fvalue in enumerate(args):
            fkey = self.packet_order[fidx]
            if fkey in fieldlist:
                retpacket[fkey] = fvalue
                fieldlist.remove(fkey)
        # check for empty fields
        if len(fieldlist) > 0:
            if zerodefault:
                for fkey in fieldlist:
                    retpacket[fkey] = 0
            else:
                raise ValueError("Missing fields in argument list: %s" % repr(fieldlist))
        return retpacket
    def register_packet_generator(self, packet_class):
        """
        Register a special packet generator class.
        
        Must be a derived class of packet
        """
        if not issubclass(packet_class, packet):
            raise TypeError("Argument 'packet_class' must derive from 'packet' class.")
        self.packet_class = packet_class

class packet(dict):
    """
    Packet base object

    This object represents a packet data, related to a protocol object. It 
    behaves exactly like a Python dictionary, but adds methods to simplify 
    packet transformations.    

    Relations with other objects:
    * It should be generated by a protocol object (and will have a reference 
      in self.protocol_ref)

    Attributes:
    * protocol_ref: protocol object that created this object.
    """
    
    # the constructor 
    def __init__(self, *args, **kwargs):
        # look for a protocol_ref key
        self.protocol_ref = kwargs.pop("protocol_ref", None)
        dict.__init__(self, *args, **kwargs)
    
# *******************************
# Additional functions
# *******************************

# Missing function in NetworkX
def all_shortest_paths(G,a,b):
    """ 
    Return a list of all shortest paths in graph G between nodes a and b
    This is a function not available in NetworkX (checked at 22-02-2011)

    Taken from: 
    http://groups.google.com/group/networkx-discuss/browse_thread/thread/55465e6bb9bae12e
    """
    ret = []
    pred = nx.predecessor(G,b)
    if not pred.has_key(a):  # b is not reachable from a
        return []
    pth = [[a,0]]
    pthlength = 1  # instead of array shortening and appending, which are relatively
    ind = 0        # slow operations, we will just overwrite array elements at position ind
    while ind >= 0:
        n,i = pth[ind]
        if n == b:
            ret.append(map(lambda x:x[0],pth[:ind+1]))
        if len(pred[n]) > i:
            ind += 1
            if ind == pthlength:
                pth.append([pred[n][i],0])
                pthlength += 1
            else:
                pth[ind] = [pred[n][i],0]
        else:
            ind -= 1
            if ind >= 0:
                pth[ind][1] += 1
    return ret
