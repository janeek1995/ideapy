import time
import cherrypy
import random

from codecs import decode
from this import s


# http://localhost:8080/examples/stream_text_app


#will stream The Zen of Python
def stream_it():
    zen = decode(s, 'rot13')

    for line in zen.split('\n'):
        time.sleep(random.randint(1, 3))
        yield bytes(line + '\n', 'utf8')


cherrypy.response.____ideapy_scope____['____ideapy____'].stream(stream_it)
