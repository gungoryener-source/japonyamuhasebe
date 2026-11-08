// T-035: `out/` (next export) için bağımlılıksız statik sunucu — yalnızca e2e testleri.
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";

const ROOT = resolve(process.argv[2] ?? "out");
const PORT = Number(process.env.PORT ?? 3100);
const TYPES = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".txt": "text/plain; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
  ".woff2": "font/woff2", ".map": "application/json",
};

function resolveFile(urlPath) {
  const rel = normalize(decodeURIComponent(urlPath.split("?")[0])).replace(/^(\.\.[/\\])+/, "");
  let p = join(ROOT, rel);
  if (!p.startsWith(ROOT)) return null;
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, "index.html");
  else if (!existsSync(p) && existsSync(`${p}.html`)) p = `${p}.html`;
  return existsSync(p) && statSync(p).isFile() ? p : null;
}

createServer((req, res) => {
  const file = resolveFile(req.url ?? "/");
  const target = file ?? join(ROOT, "404.html");
  res.writeHead(file ? 200 : 404, { "Content-Type": TYPES[extname(target)] ?? "application/octet-stream" });
  createReadStream(target).pipe(res);
}).listen(PORT, "127.0.0.1", () => console.log(`e2e static: ${ROOT} → http://127.0.0.1:${PORT}`));
