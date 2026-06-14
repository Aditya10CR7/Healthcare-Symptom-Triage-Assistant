import { createReadStream, existsSync } from "node:fs";
import { stat } from "node:fs/promises";
import { extname, join, resolve } from "node:path";
import { createServer, request } from "node:http";

const distDir = resolve("dist");
const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";
const port = Number(process.env.PORT ?? 8080);

const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

function proxyToBackend(clientReq, clientRes) {
  const target = new URL(clientReq.url ?? "/", backendOrigin);
  const proxyReq = request(
    target,
    {
      method: clientReq.method,
      headers: {
        ...clientReq.headers,
        host: target.host,
      },
    },
    (proxyRes) => {
      clientRes.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers);
      proxyRes.pipe(clientRes);
    },
  );

  proxyReq.on("error", () => {
    clientRes.writeHead(502, { "content-type": "application/json" });
    clientRes.end(JSON.stringify({ detail: "Backend is not reachable" }));
  });

  clientReq.pipe(proxyReq);
}

async function serveStatic(clientReq, clientRes) {
  const url = new URL(clientReq.url ?? "/", "http://localhost");
  const requestedPath = decodeURIComponent(url.pathname);
  let filePath = join(distDir, requestedPath);

  if (!filePath.startsWith(distDir)) {
    clientRes.writeHead(403);
    clientRes.end("Forbidden");
    return;
  }

  if (!existsSync(filePath) || (await stat(filePath)).isDirectory()) {
    filePath = join(distDir, "index.html");
  }

  const ext = extname(filePath);
  clientRes.writeHead(200, {
    "content-type": mimeTypes[ext] ?? "application/octet-stream",
  });
  createReadStream(filePath).pipe(clientRes);
}

createServer((clientReq, clientRes) => {
  const path = new URL(clientReq.url ?? "/", "http://localhost").pathname;
  if (path.startsWith("/triage") || path.startsWith("/health") || path.startsWith("/docs") || path.startsWith("/openapi.json")) {
    proxyToBackend(clientReq, clientRes);
    return;
  }
  serveStatic(clientReq, clientRes).catch(() => {
    clientRes.writeHead(500);
    clientRes.end("Server error");
  });
}).listen(port, "127.0.0.1", () => {
  console.log(`Live preview server running on http://127.0.0.1:${port}`);
});
