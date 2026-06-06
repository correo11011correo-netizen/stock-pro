from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Servidor de prueba activo")

print("Iniciando servidor de prueba en puerto 8888...")
server = HTTPServer(('0.0.0.0', 8888), SimpleHandler)
server.serve_forever()
