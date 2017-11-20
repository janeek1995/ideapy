import cherrypy
import flask_restful
import flask


# http://localhost:8080/examples/wsgi/flask_restful/?q=/hello


app = flask.Flask('test_app')
api = flask_restful.Api(app)


class HelloWorld(flask_restful.Resource):
    def get(self):
        return {'hello': 'world'}


api.add_resource(HelloWorld, '/hello')

cherrypy.response.____ideapy_scope____['____ideapy____'].run_wsgi_app(app)
