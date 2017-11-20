import cherrypy
from flask import Flask


# http://localhost:8080/examples/wsgi/flask/?q=/hello


app = Flask('test_app')

@app.route("/hello")
def hello():
    return "Hello World"


cherrypy.response.____ideapy_scope____['____ideapy____'].run_wsgi_app(app)
