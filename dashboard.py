from http.server import BaseHTTPRequestHandler, HTTPServer
import os

LOG_FILE = "/Users/jiedeng/.openclaw/workspace-cos/USVISA-CA/reschedule_persistent.log"

class LogHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # 获取最近的 150 行日志
                    tail_lines = lines[-150:]
                    content = "".join(tail_lines)
            else:
                content = "Log file not found."
        except Exception as e:
            content = f"Error reading log: {str(e)}"
            
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>USVISA-CA Live Dashboard</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body {{ 
                    background-color: #1e1e1e; 
                    color: #d4d4d4; 
                    font-family: 'Courier New', Courier, monospace; 
                    padding: 20px; 
                    line-height: 1.5;
                }}
                h2 {{ color: #569cd6; }}
                .status {{ color: #ce9178; margin-bottom: 20px; }}
                pre {{ 
                    background-color: #252526; 
                    padding: 15px; 
                    border-radius: 5px;
                    border: 1px solid #333;
                    white-space: pre-wrap; 
                    word-wrap: break-word; 
                    overflow-y: auto;
                    max-height: 80vh;
                }}
            </style>
            <script>
                // 页面加载后自动滚动到最底部
                window.onload = function() {{
                    var pre = document.getElementById("log-container");
                    pre.scrollTop = pre.scrollHeight;
                }}
            </script>
        </head>
        <body>
            <h2>USVISA-CA Live Status Monitor</h2>
            <div class="status">🟢 自动刷新中 (每 5 秒)... | 实时监控最新的 150 行日志</div>
            <pre id="log-container">{content}</pre>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

if __name__ == '__main__':
    port = 8765
    server = HTTPServer(('0.0.0.0', port), LogHandler)
    print(f"Dashboard running on http://localhost:{port}")
    server.serve_forever()
