import json
import threading
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from youtube.Stream import Stream


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def start(self):
        url = urlparse(self.path)
        params = parse_qs(url.query)
        stream = Stream(params['file'][0], 'rtmp://a.rtmp.youtube.com/live2/', params['key'][0], params['loop'][0])

        if not os.path.exists(params['file'][0]):
            return {'success': False,'message': 'file '+params['file'][0]+' not found'}


        delay = 0
        if "delay" in params:
            delay = params['delay'][0]

        threading.Thread(target=self.delay_run, args=(stream, delay)).start()

        return  {
            'success': True,
            'message': 'stream has been run',
        }

    def delay_run(self, stream,delay):

        if delay!= None:
            print ("delay run stream :"+ str(delay)+ "s")
            time.sleep(int(delay))

        stream.run()

    def stop(self):
        url = urlparse(self.path)
        params = parse_qs(url.query)
        stream = Stream(params['file'][0], 'rtmp://a.rtmp.youtube.com/live2/', params['key'][0], params['loop'][0])
        stream.stop(params['key'][0])

        return {
            'success': True,
            'message': 'stream has been stop',
        }



    def restart(self):
        url = urlparse(self.path)
        params = parse_qs(url.query)
        stream = Stream(params['file'][0], 'rtmp://a.rtmp.youtube.com/live2/', params['key'][0], params['loop'][0])
        stream.restart(params['key'][0])
        return {
            'success': True,
            'message': 'stream has been restart',
        }

    def stream(self):
        url = urlparse(self.path)
        params = parse_qs(url.query)

        stream = Stream(None, None, None, None)
        result = stream.get_stream_by_key(params['key'][0])

        response = json.dumps(result)
        self.wfile.write(response.encode())

    def route(self, argument):
        print('route')
        switcher = {
            '/start': self.start,
            '/stop': self.stop,
            '/restart': self.restart,
            '/stream': self.stream,
        }
        func = switcher.get(argument, lambda: {'error': 'some error'})
        response = json.dumps(func())
        self.wfile.write(response.encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        url = urlparse(self.path)
        self.route(url.path)


httpd = HTTPServer(('0.0.0.0', 8002), SimpleHTTPRequestHandler)

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    httpd.server_close()
