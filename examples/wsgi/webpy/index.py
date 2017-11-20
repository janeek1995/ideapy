import cherrypy
import web


# http://localhost:8080/examples/wsgi/webpy/?q=/hello


urls = (
    '/hello', 'hello'
)
app = web.application(urls, globals()).wsgifunc()

class hello:        
    def GET(self):
        return 'Hello World'


cherrypy.response.____ideapy_scope____['____ideapy____'].run_wsgi_app(app)
