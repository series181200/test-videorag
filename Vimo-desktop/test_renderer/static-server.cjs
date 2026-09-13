const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', 'dist', 'renderer');
const port = 4173;
const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

const server = http.createServer((request, response) => {
  const requestPath = decodeURIComponent((request.url || '/').split('?')[0]);
  const relativePath = requestPath === '/' ? 'index.html' : requestPath.slice(1);
  const filePath = path.resolve(root, relativePath);

  if (!filePath.startsWith(root + path.sep)) {
    response.writeHead(403);
    response.end('Forbidden');
    return;
  }

  fs.stat(filePath, (error, stats) => {
    const target = !error && stats.isFile() ? filePath : path.join(root, 'index.html');
    fs.readFile(target, (readError, data) => {
      if (readError) {
        response.writeHead(500);
        response.end('Failed to read renderer output');
        return;
      }

      response.writeHead(200, {
        'Content-Type': mimeTypes[path.extname(target)] || 'application/octet-stream',
      });
      response.end(data);
    });
  });
});

server.listen(port, '127.0.0.1', () => {
  console.log(`Renderer test server listening at http://127.0.0.1:${port}`);
});
