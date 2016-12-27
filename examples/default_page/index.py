import cherrypy

cherrypy.response.body = bytes('Hello World from default_page', 'utf8')
