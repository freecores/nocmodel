#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# NoCmodel package
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
NoCmodel package
================
  
This package includes:
  
* Module noc_base: NoCmodel Base Objects
* Module noc_guilib: NoCmodel Graphic utilities
* Module noc_tlm_base: NoCmodel TLM simulation support
* Module noc_tlm_utils: helper functions for TLM simulation
* Package basicmodels: basic examples of NoC objects (not imported by default)
"""

# required modules
import networkx as nx

# provided modules
from noc_base import *
from noc_guilib import *
from noc_tlm_base import *
from noc_tlm_utils import *

__version__ = "0.1"
