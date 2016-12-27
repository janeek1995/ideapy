import cherrypy

cherrypy.response.body = bytes('Hello World from default_page3', 'utf8')
