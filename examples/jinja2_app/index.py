import jinja2
import cherrypy

template = jinja2.Template('Hello {{ name }}!')
rendered = template.render(name='John Doe')

cherrypy.response.body = bytes(rendered, 'utf8')
