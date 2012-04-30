import os
import utils

''' `Context` provides helper methods to all `Tilt` processors. They
    are typically accessed by ERB templates. You can mix in custom
    helpers by injecting them into `Environment#context_class`. Do not
    mix them into `Context` directly.
  
      environment.context_class.class_eval do
          include MyHelper
          def asset_url
  
      <%= asset_url "foo.png" %>
  
    The `Context` also collects dependencies declared by
    assets. See `DirectiveProcessor` for an example of this.
'''
  
class Context(object):
    
    environment
    pathname
    _required_paths
    _stubbed_assets
    _dependency_paths
    _dependency_assets
    __LINE__

    def __init__(self,environment, logical_path, pathname):
      self.environment  = environment
      self._logical_path = logical_path
      self.pathname     = pathname
      self.__LINE__     = None

      self._required_paths    = []
      self._stubbed_assets    = set()
      self._dependency_paths  = set()
      self._dependency_assets = set([str(pathname)])
 
    def root_path(self):
      ''' Returns the environment path that contains the file.
          
          If `app/javascripts` and `app/stylesheets` are in your path, and
          current file is `app/javascripts/foo/bar.js`, `root_path` would
          return `app/javascripts`.
      '''
      root_path = None
      for path in self.environment.paths:
        match = re.match(path,self.pathname)
        if match:
          root_path = re.sub(match[0],'',self.pathname)

      return root_path

    def logical_path(self):
      ''' Returns logical path without any file extensions.
          
          'app/javascripts/application.js'
          # => 'application'
      '''
      filename, ext = os.path.splitext(self._logical_path_)
      return self._logical_path.rstrip(ext)

    def content_type(self):
      ''' Returns content type of file
    
          'application/javascript'
          # =>'text/css'
      '''
      return environment.content_type_of(self.pathname)

    def resolve(path, options = {}, block=None):
      ''' Given a logical path, `resolve` will find and return the fully
          expanded path. Relative paths will also be resolved. An optional
          `:content_type` restriction can be supplied to restrict the
          search.
    
          resolve("foo.js")
          # => "/path/to/app/javascripts/foo.js"
    
          resolve("./bar.js")
          # => "/path/to/app/javascripts/bar.js"
      '''
      return os.path.abspath(path)
      
    def depend_on(path):
      ''' `depend_on` allows you to state a dependency on a file without
          including it.
          
          This is used for caching purposes. Any changes made to
          the dependency file with invalidate the cache of the
          source file.
      '''
      self._dependency_paths.append(str(self.resolve(path)))

    def depend_on_asset(path):
      ''' `depend_on_asset` allows you to state an asset dependency
          without including it.
        
          This is used for caching purposes. Any changes that would
          invalidate the dependency asset will invalidate the source
          file. Unlike `depend_on`, this will include recursively include
          the target asset's dependencies.
      '''
      filename = str(self.resolve(path))
      self._dependency_assets.append(filename)

    def require_asset(path):
      ''' `require_asset` declares `path` as a dependency of the file. The
          dependency will be inserted before the file and will only be
          included once.
      '''
      pathname = self.resolve(path)
      depend_on_asset(pathname)
      self._required_paths.append(pathname)

    def stub_asset(path):
      ''' `stub_asset` blacklists `path` from being included in the bundle.
          `path` must be an asset which may or may not already be included
          in the bundle.
      '''
      self._stubbed_assets.append(str(self.resolve(path))
      
  def is_asset_requirable(path):
    ''' Tests if target path is able to be safely required into the
        current concatenation.
    '''
    pathname = self.resolve(path)
    content_type = self.environment.content_type_of(pathname)
    stat = environment.stat(path)
    
    if not stat
    return false unless stat && stat.file?
      self.content_type.nil? || self.content_type == content_type
    end

    # Reads `path` and runs processors on the file.
    #
    # This allows you to capture the result of an asset and include it
    # directly in another.
    #
    #     <%= evaluate "bar.js" %>
    #
    def evaluate(path, options = {})
      pathname   = resolve(path)
      attributes = environment.attributes_for(pathname)
      processors = options[:processors] || attributes.processors

      if options[:data]
        result = options[:data]
      else
        if environment.respond_to?(:default_external_encoding)
          mime_type = environment.mime_types(pathname.extname)
          encoding  = environment.encoding_for_mime_type(mime_type)
          result    = Sprockets::Utils.read_unicode(pathname, encoding)
        else
          result = Sprockets::Utils.read_unicode(pathname)
        end
      end

      processors.each do |processor|
        begin
          template = processor.new(pathname.to_s) { result }
          result = template.render(self, {})
        rescue Exception => e
          annotate_exception! e
          raise
        end
      end

      result
    end

    # Returns a Base64-encoded `data:` URI with the contents of the
    # asset at the specified path, and marks that path as a dependency
    # of the current file.
    #
    # Use `asset_data_uri` from ERB with CSS or JavaScript assets:
    #
    #     #logo { background: url(<%= asset_data_uri 'logo.png' %>) }
    #
    #     $('<img>').attr('src', '<%= asset_data_uri 'avatar.jpg' %>')
    #
    def asset_data_uri(path)
      depend_on_asset(path)
      asset  = environment.find_asset(path)
      base64 = Base64.encode64(asset.to_s).gsub(/\s+/, "")
      "data:#{asset.content_type};base64,#{Rack::Utils.escape(base64)}"
    end

    private
      # Annotates exception backtrace with the original template that
      # the exception was raised in.
      def annotate_exception!(exception)
        location = pathname.to_s
        location << ":#{@__LINE__}" if @__LINE__

        exception.extend(Sprockets::EngineError)
        exception.sprockets_annotation = "  (in #{location})"
      end

      def logger
        environment.logger
      end
  end
end