import cherrypy
import falcon


# http://localhost:8080/examples/wsgi/falcon/?q=/hello


api = falcon.API()

class Resource(object):
    def on_get(self, req, resp):
        resp.body = 'Hello World'
        resp.status = falcon.HTTP_200

api.add_route('/hello', Resource())


cherrypy.response.____ideapy_scope____['____ideapy____'].run_wsgi_app(api)
