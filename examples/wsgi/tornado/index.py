import cherrypy
import tornado
import tornado.web
import tornado.wsgi


# http://localhost:8080/examples/wsgi/tornado/?q=/hello


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


app = tornado.wsgi.WSGIAdapter(tornado.web.Application([
    (r"/hello", MainHandler),
]))


cherrypy.response.____ideapy_scope____['____ideapy____'].run_wsgi_app(app)
