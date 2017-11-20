import cherrypy
import bottle


# http://localhost:8080/examples/wsgi/bottle/?q=/hello


application = bottle.default_app()

@application.route('/hello')
def hello():
    return "Hello World!"

cherrypy.response.____ideapy_scope____['____ideapy____'].run_wsgi_app(application)
