// Local dev server: static files + /api/ask (same handler Vercel runs). node app/dev.js
const http = require("http"), fs = require("fs"), path = require("path");
const ask = require("./api/ask.js");
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".mp4": "video/mp4" };
http.createServer((req, res) => {
  if (req.url.startsWith("/api/ask")) return ask(req, res);
  let p = decodeURIComponent(req.url.split("?")[0]); if (p === "/") p = "/index.html";
  const f = path.join(__dirname, path.normalize(p));
  if (!f.startsWith(__dirname) || !fs.existsSync(f) || p.startsWith("/api")) { res.statusCode = 404; return res.end("not found"); }
  res.setHeader("Content-Type", types[path.extname(f)] || "application/octet-stream"); fs.createReadStream(f).pipe(res);
}).listen(process.env.PORT || 4321, () => console.log("http://localhost:" + (process.env.PORT || 4321)));
