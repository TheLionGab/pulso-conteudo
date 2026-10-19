// Servidor estático para o render.
//
// file:// bloqueia o @font-face local — a arte cai em fonte de fallback, com
// métrica e quebra de linha diferentes, e ninguém percebe até estar publicado.
// Daí o HTTP.
//
// Resolve em duas raízes: primeiro a pasta da peça, depois `engine/`. É o que
// deixa `tokens.css` e a Inter existirem uma vez só em vez de uma cópia por
// peça (cópia é como duas peças acabam com paletas diferentes).

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ENGINE_DIR = path.dirname(fileURLToPath(import.meta.url));

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.woff2': 'font/woff2',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.mp4': 'video/mp4',
};

export async function serve(pieceDir, { indexFile = 'index.html' } = {}) {
  const roots = [path.resolve(pieceDir), ENGINE_DIR];

  const server = createServer(async (req, res) => {
    const rel = decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\/+/, '');
    const name = rel || indexFile;

    for (const root of roots) {
      const file = path.join(root, name);
      // Barreira de path traversal: um `..` no caminho não pode sair da raiz.
      if (!file.startsWith(root)) continue;
      try {
        const body = await readFile(file);
        res.writeHead(200, { 'content-type': MIME[path.extname(file)] ?? 'application/octet-stream' });
        res.end(body);
        return;
      } catch {
        // tenta a próxima raiz
      }
    }

    res.writeHead(404).end();
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address();

  return {
    port,
    url(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return `http://127.0.0.1:${port}/${indexFile}${qs ? `?${qs}` : ''}`;
    },
    close: () => server.close(),
  };
}
