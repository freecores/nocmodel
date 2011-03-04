#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# NoC TLM simulation support - Utilities
#   This module declares additional helper functions 
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

from noc_tlm_base import *
from nocmodel.basicmodels import *

# helper functions
def add_tlm_basic_support(instance, **kwargs):
    """
    This function will add for every object in noc_instance a noc_tlm object
    """
    if isinstance(instance, noc):
        # add simulation object
        instance.tlmsim = noc_tlm_simulation(instance, **kwargs)
        # and add tlm objects recursively
        for obj in instance.all_list():
            altkwargs = kwargs
            altkwargs.pop("log_file", None)
            altkwargs.pop("log_level", None)
            add_tlm_basic_support(obj, **kwargs)
    elif isinstance(instance, ipcore):
        instance.tlm = basic_ipcore_tlm(instance, **kwargs)
        # don't forget internal channel
        instance.channel_ref.tlm = basic_channel_tlm(instance.channel_ref, **kwargs)
    elif isinstance(instance, router):
        instance.tlm = basic_router_tlm(instance, **kwargs)
    elif isinstance(instance, channel):
        instance.tlm = basic_channel_tlm(instance, **kwargs)
    else:
        print "Unsupported object: type %s" % type(instance)
