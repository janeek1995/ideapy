import cherrypy
import random
import string

params = cherrypy.request.body.params

length = int(cherrypy.request.body.params['length'])
random_text = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))

cherrypy.response.body = bytes(random_text, 'utf8')
