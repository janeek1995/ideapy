import time
import cherrypy
import random

from codecs import decode
from this import s

#will stream The Zen of Python

#for Chrome and IE
cherrypy.response.headers['X-Content-Type-Options'] = 'nosniff'


def stream():
    zen = decode(s, 'rot13')

    for line in zen.split('\n'):
        time.sleep(random.randint(1, 3))
        yield bytes(line + '\n', 'utf8')
