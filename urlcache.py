#!/usr/bin/python
# Comics Grabber by Tom Parker <palfrey@tevp.net>
# http://tevp.net
#
# URL Caching class
# Caches retrieved URLs, with some comic-optimised sections
#
# Released under the GPL Version 2 (http://www.gnu.org/copyleft/gpl.html)

import os,md5
from cPickle import dump,load
try:
	from urlgrab import URLTimeout
except ImportError:
	from sys import exit
	print "Get urlgrab with 'git clone git://github.com/palfrey/urlgrab.git'"
	exit(1)
import urllib2
from os.path import exists

debug = True

class CacheError(Exception):
	pass	

class URLCache:
	STAT_START = 1
	STAT_NEW = 2
	STAT_UNCHANGED = 3
	STAT_FAILED = 4

	def __init__(self,cache_dir,proxy=None):
		self.store = {}
		self.cache = cache_dir
		self.proxy = proxy
		if not os.path.exists(self.cache):
			os.makedirs(self.cache)
		else:
			for f in os.listdir(self.cache):
				try:
					old = load(file(os.path.join(self.cache,f)))
					if old.mime[0] == "image":
						old.status = self.STAT_UNCHANGED
					else:
						old.status = self.STAT_START
					old.used = False
					self.store[self.md5(old.url,old.ref)] = old

				except (EOFError, ValueError): # ignore and discard
					os.unlink(os.path.join(self.cache,f))
	
	def cleanup(self):
		for h in self.store.keys():
			if self.store[h].status != self.STAT_FAILED and (not self.store[h].__dict__.has_key("used") or self.store[h].used == False):
				p =os.path.join(self.cache,h)
				if exists(p):
					os.unlink(p)
				
	def md5(self,url,ref):
		m = md5.new()
		m.update(url)
		m.update(str(ref))
		return m.hexdigest()
	
	def set_varying(self,url,ref=None):
		hash = self.md5(url,ref)
		if self.store.has_key(hash):
			self.store[hash].status = self.STAT_START

	def used(self,url,ref=None):
		hash = self.md5(url,ref)
		if self.store.has_key(hash):
			self.store[hash].used = True
	
	def get(self,url,ref=None):
		url = url.replace("&amp;","&")
		hash = self.md5(url,ref)
		if self.store.has_key(hash):
			old = self.store[hash]
		else:
			old = URLData(url,ref)
			self.store[hash] = old
		if old.status == self.STAT_FAILED:
			return None
		
		if old.status == self.STAT_START:
			try:
				#if ref==None:
				#	data = urllib2.urlopen(url)
				#else:
				#	r = urllib2.Request(url)
				#	r.add_header("Referer",ref)
				#	data = urllib2.urlopen(r)
				data = URLTimeout.URLTimeout().get_url(url,ref=ref,proxy=self.proxy)

			except urllib2.HTTPError,err:
				if err.code==404:
					return None
				else:
					if ref!=None:
						refpath = os.path.join(self.cache,self.md5(ref,None))
						if os.path.exists(refpath):
							os.unlink(refpath)
							print "Destroyed",refpath,"because of error!"
					self.gen_failed(old)
					raise CacheError, err.msg+" while getting <a href=\""+url+"\">"+url+"</a>"
			except urllib2.URLError,err:
				self.gen_failed(old)
				raise CacheError, err.reason[1]+" while getting <a href=\""+url+"\">"+url+"</a>"
			
			except URLTimeout.URLTimeoutError, err:
				#self.gen_failed(old)
				raise CacheError, str(err)+" while getting <a href=\""+url+"\">"+url+"</a>"

			content = data.read()
			if old.content!=content:
				old.status = self.STAT_NEW
				old.content = content
				old.length = len(content)
				try:
					old.mime = (data.info().getmaintype(),data.info().getsubtype())
				except:
					return None
				f = file(os.path.join(self.cache,hash),'wb')
				dump(old,f,False)
			else:
				old.status = self.STAT_UNCHANGED
		old.used = True
		return old

	def gen_failed(self,old):
		old.status = self.STAT_FAILED
		old.content = ""
		old.length = 0
		old.mime = ("","")

	def get_mult(self,url,ref=None,count=1):
		retry = 0
		while retry<count:
			try:
				return self.get(url,ref)
			except CacheError,err:
				if str(err).find("Timed out")==-1:
					break
				retry += 1
				if retry!=count:
					print "retrying..."

		hash = self.md5(url,ref)
		self.store[hash] = URLData(url,ref)
		self.gen_failed(self.store[hash])
		raise

class URLData:
	def __init__(self,url,ref):
		self.url = url
		self.ref = ref
		self.content = ""
		self.status = URLCache.STAT_START
		self.mime = ("","")
		
		
	
