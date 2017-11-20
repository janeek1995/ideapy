import cherrypy


# http://localhost:8080/examples/html


# you can also use regular .html file instead of .py
# see examples/html2


cherrypy.response.headers['Content-Type'] = 'text/html'

cherrypy.response.body = bytes("""<!DOCTYPE html>
<html>
<body>

<p>I am normal</p>
<p style="color:red;">I am red</p>
<p style="color:blue;">I am blue</p>
<p style="font-size:36px;">I am big</p>

</body>
</html>
""", 'utf8')
