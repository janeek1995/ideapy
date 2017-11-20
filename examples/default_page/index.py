import cherrypy

# http://localhost:8080/examples/default_page


cherrypy.response.body = bytes('Hello World from default_page', 'utf8')
