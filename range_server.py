import http.server
import socketserver
import os
import re

PORT = 8000

class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        range_header = self.headers.get('Range')
        path = self.translate_path(self.path)

        if not range_header or os.path.isdir(path) or not os.path.exists(path):
            return super().do_GET()

        try:
            total_size = os.path.getsize(path)
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if not match:
                return super().do_GET()

            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else total_size - 1

            if start >= total_size or end >= total_size or start > end:
                self.send_error(416, 'Requested Range Not Satisfiable')
                return

            self.send_response(206)
            self.send_header('Content-Type', self.guess_type(path))
            self.send_header('Content-Range', f'bytes {start}-{end}/{total_size}')
            self.send_header('Content-Length', str(end - start + 1))
            self.send_header('Last-Modified', self.date_time_string(os.path.getmtime(path)))
            self.end_headers()

            with open(path, 'rb') as f:
                f.seek(start)
                bytes_to_read = end - start + 1
                chunk_size = 64 * 1024
                while bytes_to_read > 0:
                    current_chunk = min(chunk_size, bytes_to_read)
                    data = f.read(current_chunk)
                    if not data:
                        break
                    self.wfile.write(data)
                    bytes_to_read -= len(data)
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            self.send_error(500, str(e))

if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), RangeRequestHandler) as httpd:
        print(f"Serving HTTP with Range Support on port {PORT}")
        httpd.serve_forever()
