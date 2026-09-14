const http = require('http');
const fs   = require('fs');
const path = require('path');

const FILE = path.join(__dirname, 'industrial_ai_platform.html');
const PORT = 7842;

const server = http.createServer((req, res) => {
  fs.readFile(FILE, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not found'); return; }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(data);
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log('Server running at http://localhost:' + PORT);
});
