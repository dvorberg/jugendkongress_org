import sys
from flup.server.fcgi import WSGIServer
from juko.app_factory import create_app

# From
# https://flask.palletsprojects.com/en/1.1.x/deploying/fastcgi/#configuring-apache

class ScriptNameStripper(object):
   def __init__(self, app):
       self.app = app

   def __call__(self, environ, start_response):
       for a in ("SCRIPT_FILENAME", "PATH_TRANSLATED"):
          environ[a] = environ[a].replace("site.wrapper/", "")

       #for key in environ.keys():
       #   if type(environ[key]) == str:
       #      environ[key] = environ[key].replace(
       #         "/home/web/jugendkongress/www/", "/").replace("%3f", "?")

       return self.app(environ, start_response)

def myapp(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    end = []
    for name, value in environ.items():
       end.append(f"{name}={repr(value)}")

    return "\n".join(end)

if __name__ == '__main__':
   #WSGIServer(ScriptNameStripper(myapp)).run()
   WSGIServer(ScriptNameStripper(create_app().wsgi_app)).run()
