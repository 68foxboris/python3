#!/usr/bin/python
# -*- coding: utf-8 -*-
from Components.Renderer.Renderer import Renderer

from enigma import eLabel


class FixedLabel(Renderer):
	GUI_WIDGET = eLabel
