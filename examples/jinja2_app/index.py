import jinja2
import cherrypy

# http://localhost:8080/examples/jinja2_app


template = jinja2.Template('Hello {{ name }}!')
rendered = template.render(name='John Doe')

cherrypy.response.body = bytes(rendered, 'utf8')
