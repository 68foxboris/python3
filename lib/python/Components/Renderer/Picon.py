#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import re
from Components.Renderer.Renderer import Renderer
from enigma import ePixmap
from Tools.Alternatives import GetWithAlternative
from Tools.Directories import pathExists, SCOPE_GUISKIN, resolveFilename, sanitizeFilename
from Components.Harddisk import harddiskmanager
from ServiceReference import ServiceReference
from six import PY2


class PiconLocator:
	def __init__(self, piconDirectories=['picon']):
		harddiskmanager.on_partition_list_change.append(self.__onPartitionChange)
		self.piconDirectories = piconDirectories
		self.activePiconPath = None
		self.searchPaths = []
		for mp in ('/usr/share/enigma2/', '/'):
			self.__onMountpointAdded(mp)
		for part in harddiskmanager.getMountedPartitions():
			self.__onMountpointAdded(part.mountpoint)

	def __onMountpointAdded(self, mountpoint):
		for piconDirectory in self.piconDirectories:
			try:
				path = os.path.join(mountpoint, piconDirectory) + '/'
				if os.path.isdir(path) and path not in self.searchPaths:
					for fn in os.listdir(path):
						if fn.endswith('.png') or fn.endswith('.svg'):
							print("[Picon] adding path:", path)
							self.searchPaths.append(path)
							break
			except:
				pass

	def __onMountpointRemoved(self, mountpoint):
		for piconDirectory in self.piconDirectories:
			path = os.path.join(mountpoint, self.piconDirectories) + '/'
			try:
				self.searchPaths.remove(path)
				print("[Picon] removed path:", path)
			except:
				pass

	def __onPartitionChange(self, why, part):
		if why == 'add':
			self.__onMountpointAdded(part.mountpoint)
		elif why == 'remove':
			self.__onMountpointRemoved(part.mountpoint)

	def findPicon(self, serviceName):
		if self.activePiconPath is not None:
			for ext in ('.png', '.svg'):
				pngname = self.activePiconPath + serviceName + ext
				if pathExists(pngname):
					return pngname
		else:
			for path in self.searchPaths:
				for ext in ('.png', '.svg'):
					pngname = path + serviceName + ext
					if pathExists(pngname):
						self.activePiconPath = path
						return pngname
		return ""

	def addSearchPath(self, value):
		if pathExists(value):
			if not value.endswith('/'):
				value += '/'
			if not value.startswith('/media/net') and not value.startswith('/media/autofs') and value not in self.searchPaths:
				self.searchPaths.append(value)

	def getPiconName(self, serviceName):
		#remove the path and name fields, and replace ':' by '_'
		fields = GetWithAlternative(serviceName).split(':', 10)[:10]
		if not fields or len(fields) < 10:
			return ""
		pngname = self.findPicon('_'.join(fields))
		if not pngname and not fields[6].endswith("0000"):
			#remove "sub-network" from namespace
			fields[6] = fields[6][:-4] + "0000"
			pngname = self.findPicon('_'.join(fields))
		if not pngname and fields[0] != '1':
			#fallback to 1 for IPTV streams
			fields[0] = '1'
			pngname = self.findPicon('_'.join(fields))
		if not pngname and fields[2] != '2':
			#fallback to 1 for TV services with non-standard service types
			fields[2] = '1'
			pngname = self.findPicon('_'.join(fields))
		if not pngname: # picon by channel name
			name = sanitizeFilename(ServiceReference(serviceRef).getServiceName())
			name = re.sub('[^a-z0-9]', '', name.replace('&', 'and').replace('+', 'plus').replace('*', 'star').lower())
			if len(name) > 0:
				pngname = self.findPicon(name)
				if not pngname and len(name) > 2 and name.endswith('hd'):
					pngname = self.findPicon(name[:-2])
				if not pngname and len(name) > 6:
					series = re.sub(r's[0-9]*e[0-9]*$', '', name)
					pngname = self.findPicon(series)
		if not pngname: # picon default
			tmp = resolveFilename(SCOPE_GUISKIN, 'picon_default.png') # picon_default in current active skin
			tmp2 = self.findPicon("picon_default") # picon_default in picon folder
			if pathExists(tmp2):
				pngname = tmp2
			else:
				if pathExists(tmp):
					pngname = tmp
				else:
					pngname = resolveFilename(SCOPE_GUISKIN, 'picon_default.png')
		return pngname


piconLocator = None


def initPiconPaths():
	global piconLocator
	piconLocator = PiconLocator()


initPiconPaths()


def getPiconName(serviceName):
	return piconLocator.getPiconName(serviceName)


class Picon(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.pngname = None
		self.defaultpngname = resolveFilename(SCOPE_GUISKIN, "picon_default.png")

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				piconLocator.addSearchPath(value)
				attribs.remove((attrib, value))
		self.skinAttributes = attribs
		rc = Renderer.applySkin(self, desktop, parent)
		self.changed((self.CHANGED_DEFAULT,))
		return rc

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			if what[0] in (self.CHANGED_DEFAULT, self.CHANGED_ALL, self.CHANGED_SPECIFIC):
				pngname = piconLocator.getPiconName(self.source.text)
				if not pathExists(pngname): # no picon for service found
					pngname = self.defaultpngname
				if self.pngname != pngname:
					if pngname:
						self.instance.setScale(1)
						self.instance.setPixmapFromFile(pngname)
						self.instance.show()
					else:
						self.instance.hide()
					self.pngname = pngname
			elif what[0] == self.CHANGED_CLEAR:
				self.pngname = None
				self.instance.hide()
