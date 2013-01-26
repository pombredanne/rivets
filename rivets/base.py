import os
import re
from hashlib import md5
import json
import copy

from assets import Asset, AssetAttributes, BundledAsset, ProcessedAsset, StaticAsset
from errors import FileNotFound


class Base(object):

	default_encoding = 'utf8'
	_digest = None

	@property
	def digest(self):

		if not self._digest:
			from version import VERSION
			self._digest = md5()
			self._digest.update(str(VERSION))
			self._digest.update(str(self.version))

		return self._digest.copy()

	def get_file_digest(self,path):
		digest = self.digest
		if os.path.isfile(path):
			data = open(path).read()
			digest.update(data)
		elif os.path.isdir(path):
			entries = self.search_path.entries(path)
			digest.update(','.join(entries).encode('utf8'))
		return digest

	@property
	def root(self):
		return copy.deepcopy(self.search_path.root)

	@property
	def paths(self):
		return copy.deepcopy(self.search_path.paths)

	@property
	def extensions(self):
		return copy.deepcopy(self.search_path.extensions)

	def prepend_path(self,*paths):
		self.prepend_paths(*paths)

	def prepend_paths(self,*paths):
		self.expire_index()
		self.search_paths.append_paths(*paths)

	def append_path(self,*paths):
		self.append_paths(*paths)

	def append_paths(self,*paths):
		self.expire_index()
		self.search_path.append_paths(*paths)

	def clear_paths(self):
		self.expire_index()
		for path in copy.deepcopy(self.search_path.paths):
			self.search_path.paths.remove_path(path)

	def register_mimetype(self,extension,mimetype):
		self.expire_index()
		self.mimetypes.register_mimetype(extension,mimetype)
		self.search_path.append_extension(extension)

	def register_engine(self,extension,engine):
		self.expire_index()
		self.engines.register_engine(extension,engine)
		self.add_engine_to_search_path(extension,engine)

	def register_preprocessor(self,mimetype,processor,callback=None):
		self.expire_index()
		self.processors.register_preprocessor(mimetype,processor,callback)

	def unregister_preprocessor(self,mimetype,processor):
		self.expire_index()
		self.processors.unregister_preprocessor(mimetype,processor)

	def register_postprocessor(self,mimetype,processor,callback=None):
		self.expire_index()
		self.processors.register_postprocessor(mimetype,processor,callback)

	def unregister_postprocessor(self,mimetype,processor):
		self.expire_index()
		self.processors.unregister_postprocessor(mimetype,processor)

	def register_bundleprocessor(self,mimetype,processor,callback=None):
		self.expire_index()
		self.processors.register_bundleprocessor(mimetype,processor,callback)

	def unregister_bundleprocessor(self,mimetype,processor):
		self.expire_index()
		self.processors.unregister_bundleprocessor(mimetype,processor)

	def set_js_compressor(self,compressor):
		self.processors.set_js_compressor(compressor)

	def set_css_compressor(self,compressor):
		self.processors.set_css_compressor(compressor)

	def add_engine_to_search_path(self,extension,engine):
		self.search_path.append_extension(extension)

		if getattr(engine,'default_mime_type',None):
			format_ext = self.mimetypes.get_extension_for_mimetype(engine.default_mime_type)
			if format_ext:
				self.search_path.alias_extension(extension, format_ext)

	@property
	def index(self):
		raise NotImplementedError('Index Not Implemented in Base class')

	def entries(self,path):
		return self.search_path.entries(path)

	def stat(self,path):
		return self.search_path.stat(path)

	def get_attributes_for(self,path):
		return AssetAttributes(self,path)

	def get_content_type_of(self,path):
		return self.get_attributes_for(path).content_type

	def __getitem__(self,path):
		return self.find_asset(path)

	def find_asset(self,path,**options):
		logical_path = path

		if os.path.isabs(path):
			if not self.stat(path):
				return None
			logical_path = self.get_attributes_for(path).logical_path
		else:
			try:
				path = self.resolve(logical_path)

				filename,extname = os.path.splitext(path)

				if extname == "":
					expanded_logical_path = self.get_attributes_for(path).logical_path
					newfile,newext = os.path.splitext(expanded_logical_path)
					logical_path += newext
			except FileNotFound:
				return None

		return self.build_asset(logical_path,path,**options)

	def build_asset(self,logical_path,path,**options):

		if not options.has_key('bundle'):
			options["bundle"] = True

		if self.get_attributes_for(path).processors:

			if not options['bundle']:
				return ProcessedAsset(self,logical_path,path)
			else:
				return BundledAsset(self,logical_path,path)
		else:
			return StaticAsset(self,logical_path,path)

	def resolve(self,logical_path,**options):

		if options.has_key('callback') and options['callback']:
			callback = options.pop('callback')
			def process_asset(paths):
				if paths:
					for path in paths:
						if os.path.basename(path)=='component.json':
							component = json.loads(open(path).read())

							if component.has_key('main'):
								if isinstance(component['main'],str):
									return options['callback'](os.path.join(os.path.dirname(path),component['main']))
								elif isinstance(component['main'],list):
									filename,ext = os.path.splitext(logical_path)

									for fn in component['main']:
										fn_name,fn_ext = os.path.splitext(fn)
										if ext == "" or ext == fn_ext:
											asset = callback(os.path.join(os.path.dirname(path),fn))
											if asset:
												return asset

						else:
							asset = callback(path)
							if asset:
								return asset

			args = self.get_attributes_for(logical_path).search_paths
			asset = self.search_path.find(callback=process_asset,*args,**options)
			
		else:
			options['callback'] = lambda x: x
			asset = self.resolve(logical_path,**options)
		if asset:
			return asset
		raise FileNotFound("Couldn't find file %s" % logical_path)

	def compile(self,path):
		
		asset = self.find_asset(path)
		return asset.to_string()

	def each_entry(self,root,callback=None):

		if not callback:
			return 
			
		paths = []
		for filename in sorted(self.entries(root)):
			path = os.path.join(root,filename)
			paths.append(path)

			if os.path.isdir(path):
				self.each_entry(path,callback= lambda x:paths.append(x))

		for path in sorted(paths):
			callback(path)

	def each_file(self,callback=None):

		if not callback:
			return

		for root in self.paths:
			def do(path):
				if os.path.isdir(path):
					callback(path)

			self.each_entry(root,callback=do)

	def each_logical_path(self,callback=None,*args):

		if not callback:
			return

		filters = [item for sublist in args for item in sublist]
		files = {}

		def do(filename):
			logical_path = self.logical_path_for_fullname(filename,filters)
			if logical_path:
				if not files.has_key(logical_path):
					callback(logical_path,filename)

				files[logical_path] = True

		self.each_file(callback=do)

	def logical_path_for_fullname(self,filename,filters):
		logical_path = self.get_attributes_for(filename).logical_path

		if self.matches_filter(filters,logical_path,filename):
			return logical_path

		pieces = re.split(r"""[^\.]+""",os.path.basename(logical_path))
		if pieces[0] == 'index':
			path = re.replace(r"""\/index\.""",".",logical_path)
			if self.matches_filter(filters,path,filename):
				return path


		return None

	def matches_filter(self,filters,logical_path,filename):
		if filters == []:
			return True

		match = False
		for filter in filters:
			if isinstance(filter,re.RegexObject):
				if filter.search(logical_path):
					match = True
					break

			elif hasattr(filter,'__call__'):
				if filter.__call__(logical_path,filename):
					match = True
					break

			else:
				import fnmatch
				if fnmatch.fnmatch(str(filter),logical_path):
					match = True
					break

		return match

	###########
	# Caching #
	###########

	def cache_key_for(self,path,**options):
		return "%s:%i" % (path,1 if options.has_key('bundle') and options['bundle'] else 0)

	def cache_get(self,key):

		if hasattr(self.cache,'get'):
			return self.cache.get(key)

		return None

	def cache_set(self,key,value):

		if hasattr(self.cache,'set'):
			return self.cache.set(key,value)

	def cache_asset(self,path,callback=None):

		if self.cache is None:
			return callback()
		else:
			asset = Asset.from_hash(self,self.cache_get_hash(path))
			if asset and asset.is_fresh(self):
				return asset
			elif callback:
				asset = callback()

				if asset:
					asset_hash = {}
					asset_hash = asset.encode_with(asset_hash)

					self.cache_set_hash(path,asset_hash)

					if path != asset.pathname:
						self.cache_set_hash(asset.pathname,asset_hash)

					return asset

		return None

	def expand_cache_key(self,key):
		h = md5()
		h.update(key.replace(self.root,''))
		return os.path.join('rivets',h.hexdigest())

	def cache_get_hash(self,key):
		asset_hash = self.cache_get(self.expand_cache_key(key))
		if asset_hash and isinstance(asset_hash,dict) and self.digest.hexdigest() == asset_hash['_version']:
			return asset_hash

		return None

	def cache_set_hash(self,key,asset_hash):
		asset_hash['_version'] = self.digest.hexdigest()
		self.cache_set(self.expand_cache_key(key),asset_hash)
		return asset_hash