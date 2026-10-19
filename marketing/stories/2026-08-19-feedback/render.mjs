#!/usr/bin/env node
// Renderiza a campanha de Stories a partir de src/story.html.
//
// Saídas em out/:
//   story-{1,2,3}.png        arte final, limpa, pronta para postar
//   story-{1,2,3}-guia.jpg   mesma arte com a zona do sticker demarcada
//   story-{1,2,3}.mp4        versão animada de 6s de cada peça (H.264/yuv420p)
//
// Sem dependência de npm: fala CDP direto com o Chromium que já vem na imagem
// (o mesmo que o Playwright usa) e encoda com o ffmpeg que vem junto. Instalar
// playwright aqui só para tirar screenshot mexeria no lockfile do monorepo por
// causa de uma peça de marketing — não vale.
//
// Uso:
//   node marketing/stories/2026-08-19-feedback/render.mjs           # tudo
//   node marketing/stories/2026-08-19-feedback/render.mjs --no-video

import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { mkdir, mkdtemp, readFile, rm, writeFile, readdir } from 'node:fs/promises';
import os from 'node:os';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(HERE, 'src');
const OUT = path.join(HERE, 'out');

const WIDTH = 1080;
const HEIGHT = 1920;
const REST_T = 2600; // instante em que toda a animação já terminou
const VIDEO_FPS = 30;
const VIDEO_MS = 6000;

const CHROMIUM = firstExisting([
  '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  '/opt/pw-browsers/chromium/chrome-linux/chrome',
  process.env.CHROMIUM_PATH,
]);
// Ordem importa: o ffmpeg que vem com o Playwright é uma build mínima (só VP8/
// WebM) e o Instagram não aceita WebM. Um ffmpeg completo do sistema vem antes.
const FFMPEG = firstExisting([
  process.env.FFMPEG_PATH,
  '/opt/homebrew/bin/ffmpeg',
  '/usr/local/bin/ffmpeg',
  '/usr/bin/ffmpeg',
]);

function firstExisting(candidates) {
  for (const c of candidates) if (c && existsSync(c)) return c;
  return null;
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.woff2': 'font/woff2',
  '.svg': 'image/svg+xml',
};

/** Serve src/ por HTTP: file:// bloqueia o @font-face local e a arte cai no fallback. */
async function serveSrc() {
  const server = createServer(async (req, res) => {
    const rel = decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\/+/, '');
    const file = path.join(SRC, rel || 'story.html');
    if (!file.startsWith(SRC)) {
      res.writeHead(403).end();
      return;
    }
    try {
      const body = await readFile(file);
      res.writeHead(200, { 'content-type': MIME[path.extname(file)] ?? 'application/octet-stream' });
      res.end(body);
    } catch {
      res.writeHead(404).end();
    }
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  return { server, port: server.address().port };
}

async function launchChromium() {
  if (!CHROMIUM) throw new Error('Chromium não encontrado. Defina CHROMIUM_PATH.');
  // Perfil fora de out/: o Chromium ainda está gravando quando o script termina,
  // e apagar a pasta na hora do finally dava ENOTEMPTY.
  const profile = await mkdtemp(path.join(os.tmpdir(), 'pdc-stories-'));
  const child = spawn(
    CHROMIUM,
    [
      '--headless=new',
      '--remote-debugging-port=0',
      '--no-sandbox',
      '--disable-gpu',
      '--hide-scrollbars',
      '--force-device-scale-factor=1',
      // Determinismo tipográfico: sem hinting e sem subpixel, o mesmo t gera o
      // mesmo PNG em qualquer máquina — o que torna o diff da arte auditável.
      '--font-render-hinting=none',
      '--disable-font-subpixel-positioning',
      '--disable-lcd-text',
      '--disable-dev-shm-usage',
      `--user-data-dir=${profile}`,
      'about:blank',
    ],
    { stdio: ['ignore', 'pipe', 'pipe'] },
  );

  const wsUrl = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Chromium não abriu o DevTools em 30s')), 30_000);
    let buf = '';
    child.stderr.on('data', (chunk) => {
      buf += chunk;
      const m = buf.match(/ws:\/\/127\.0\.0\.1:\d+\/devtools\/browser\/[\w-]+/);
      if (m) {
        clearTimeout(timer);
        resolve(m[0]);
      }
    });
    child.on('exit', (code) => reject(new Error(`Chromium saiu com código ${code}`)));
  });

  return { child, wsUrl, profile };
}

/** Cliente CDP mínimo sobre o WebSocket nativo do Node 22. */
class Cdp {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      const p = this.pending.get(msg.id);
      if (!p) return;
      this.pending.delete(msg.id);
      msg.error ? p.reject(new Error(`${msg.error.message} (${p.method})`)) : p.resolve(msg.result);
    });
  }

  static async connect(url) {
    const ws = new WebSocket(url);
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, { once: true });
      ws.addEventListener('error', () => reject(new Error(`falha ao conectar em ${url}`)), { once: true });
    });
    return new Cdp(ws);
  }

  send(method, params = {}, sessionId) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, method });
      this.ws.send(JSON.stringify({ id, method, params, sessionId }));
    });
  }
}

async function openPage(browser) {
  const { targetId } = await browser.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await browser.send('Target.attachToTarget', { targetId, flatten: true });
  const call = (method, params) => browser.send(method, params, sessionId);

  await call('Page.enable');
  await call('Runtime.enable');
  await call('Emulation.setDeviceMetricsOverride', {
    width: WIDTH,
    height: HEIGHT,
    deviceScaleFactor: 1,
    mobile: false,
  });
  return { call, targetId };
}

async function evaluate(call, expression) {
  const { result, exceptionDetails } = await call('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (exceptionDetails) throw new Error(exceptionDetails.text ?? 'erro no page script');
  return result.value;
}

/** Navega e só devolve quando fonte + layout estabilizaram (data-ready do HTML). */
async function goto(call, url) {
  await call('Page.navigate', { url });
  const deadline = Date.now() + 20_000;
  for (;;) {
    const ready = await evaluate(call, 'document.documentElement.dataset.ready === "1"').catch(() => false);
    if (ready) break;
    if (Date.now() > deadline) throw new Error(`página não ficou pronta: ${url}`);
    await new Promise((r) => setTimeout(r, 50));
  }
  // Dois rAF: garante que o estilo congelado já entrou em um frame composto.
  await evaluate(call, 'new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))');
}

/**
 * Gate de layout. A peça é feita para 1080x1920 com 250/320 de safe area — se o
 * texto crescer e vazar, o Instagram corta a frase e ninguém percebe até o post
 * estar no ar. Falhar aqui é melhor que exportar PNG torto.
 */
async function assertFits(call, label) {
  const box = await evaluate(
    call,
    `(() => {
       const c = document.querySelector('.content');
       const h1 = document.querySelector('h1');
       return {
         overflow: c.scrollHeight - c.clientHeight,
         wide: Math.max(0, h1.scrollWidth - h1.clientWidth),
         lines: h1.querySelectorAll('.line').length,
         h1Height: h1.getBoundingClientRect().height,
       };
     })()`,
  );
  if (box.overflow > 0) throw new Error(`${label}: conteúdo vaza ${box.overflow}px da safe area`);
  if (box.wide > 0) throw new Error(`${label}: título vaza ${box.wide}px na horizontal`);
  // 1.05 de line-height sobre 88px = 92.4px por linha. Mais que isso significa
  // que alguma linha do título quebrou sozinha e o ritmo do bloco se perdeu.
  const maxHeight = box.lines * 93 + 4;
  if (box.h1Height > maxHeight) {
    throw new Error(`${label}: título quebrou linha extra (${Math.round(box.h1Height)}px > ${maxHeight}px)`);
  }
  return box;
}

/**
 * `format`: PNG para a arte final; JPEG q=95 para os quadros intermediários do
 * vídeo. Codificar 180 PNGs de 1080x1920 dominava o tempo de render (~1,3s por
 * quadro) e o ganho é invisível depois do H.264.
 */
async function shoot(call, file, format = 'png') {
  const { data } = await call('Page.captureScreenshot', {
    format,
    ...(format === 'jpeg' ? { quality: 95 } : {}),
    captureBeyondViewport: false,
    clip: { x: 0, y: 0, width: WIDTH, height: HEIGHT, scale: 1 },
  });
  const buf = Buffer.from(data, 'base64');
  await writeFile(file, buf);
  return buf;
}

function url(port, params) {
  return `http://127.0.0.1:${port}/story.html?${new URLSearchParams(params)}`;
}

/**
 * Valida o MP4 depois de encodado, decodificando de ponta a ponta. Checar só o
 * tamanho do arquivo não prova nada: um MP4 truncado ou com contagem de quadros
 * errada abre no Finder e falha no upload do Instagram.
 */
async function validateMp4(bin, file, expectedFrames) {
  const log = await new Promise((resolve, reject) => {
    const p = spawn(bin, ['-hide_banner', '-i', file, '-f', 'null', '-'], {
      stdio: ['ignore', 'ignore', 'pipe'],
    });
    let buf = '';
    p.stderr.on('data', (d) => (buf += d));
    p.on('error', reject);
    p.on('exit', () => resolve(buf));
  });

  const stream = log.match(/Stream #0:0.*Video: (.+)/)?.[1] ?? '';
  const problems = [];
  if (!/\bh264\b/.test(stream)) problems.push(`codec não é H.264: ${stream}`);
  if (!stream.includes('yuv420p')) problems.push('pix_fmt não é yuv420p (Instagram recusa)');
  if (!stream.includes(`${WIDTH}x${HEIGHT}`)) problems.push(`dimensão errada: esperado ${WIDTH}x${HEIGHT}`);
  if (!stream.includes(`${VIDEO_FPS} fps`)) problems.push(`fps errado: esperado ${VIDEO_FPS}`);
  if (/Audio:/.test(log)) problems.push('faixa de áudio inesperada');

  const decoded = Number([...log.matchAll(/frame=\s*(\d+)/g)].at(-1)?.[1] ?? 0);
  if (decoded !== expectedFrames) {
    problems.push(`decodificou ${decoded} quadros, esperado ${expectedFrames}`);
  }

  // faststart: o átomo moov tem que vir antes do mdat, senão o player precisa do
  // arquivo inteiro antes de começar — é o que trava upload em conexão de campo.
  const head = await readFile(file);
  const moov = head.indexOf('moov');
  const mdat = head.indexOf('mdat');
  if (moov < 0 || mdat < 0 || moov > mdat) problems.push('sem faststart (moov depois do mdat)');

  if (problems.length) throw new Error(`${path.basename(file)} inválido:\n  - ${problems.join('\n  - ')}`);
  return { stream: stream.trim(), frames: decoded };
}

/** Confere que o ffmpeg escolhido encoda H.264 antes de gastar 3 min de render. */
async function assertH264(bin) {
  const out = await new Promise((resolve, reject) => {
    const p = spawn(bin, ['-hide_banner', '-encoders'], { stdio: ['ignore', 'pipe', 'ignore'] });
    let buf = '';
    p.stdout.on('data', (d) => (buf += d));
    p.on('error', reject);
    p.on('exit', () => resolve(buf));
  });
  if (!out.includes('libx264')) {
    throw new Error(
      `ffmpeg em ${bin} não tem libx264 — o MP4 do Instagram exige H.264.\n` +
        'Instale um ffmpeg completo (macOS: brew install ffmpeg) ou aponte FFMPEG_PATH para ele.',
    );
  }
}

async function run(bin, args) {
  await new Promise((resolve, reject) => {
    const p = spawn(bin, args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let err = '';
    p.stderr.on('data', (d) => (err += d));
    p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`${path.basename(bin)} falhou (${code}):\n${err.slice(-1500)}`))));
  });
}

async function main() {
  const withVideo = !process.argv.includes('--no-video');
  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });

  const { server, port } = await serveSrc();
  const { child, wsUrl, profile } = await launchChromium();
  const browser = await Cdp.connect(wsUrl);
  const { call } = await openPage(browser);

  const manifest = [];

  try {
    // 1. Artes estáticas — limpa e com guia de sticker.
    for (const frame of [1, 2, 3]) {
      for (const guide of [0, 1]) {
        // A arte que sobe é PNG (texto sobre gradiente, sem artefato). O guia é
        // material de consulta interna, então sai em JPEG e economiza ~1,2 MB
        // por arquivo no repositório.
        const name = guide ? `story-${frame}-guia.jpg` : `story-${frame}.png`;
        await goto(call, url(port, { frame, guide, t: REST_T }));
        await assertFits(call, name);
        const buf = await shoot(call, path.join(OUT, name), guide ? 'jpeg' : 'png');
        manifest.push({ file: name, bytes: buf.length, sha256: sha(buf) });
        console.log(`✓ ${name} (${(buf.length / 1024).toFixed(0)} kB)`);
      }
    }

    // 2. Vídeo de cada peça: um quadro por instante, sem depender de wall clock.
    if (withVideo) {
      if (!FFMPEG) throw new Error('ffmpeg não encontrado. Defina FFMPEG_PATH.');
      await assertH264(FFMPEG);
      const total = Math.round((VIDEO_MS / 1000) * VIDEO_FPS);

      for (const frame of [1, 2, 3]) {
        const name = `story-${frame}.mp4`;
        const frames = path.join(OUT, '.frames');
        await rm(frames, { recursive: true, force: true });
        await mkdir(frames, { recursive: true });

        await goto(call, url(port, { frame, guide: 0, t: REST_T }));
        await assertFits(call, name);

        const started = Date.now();
        for (let i = 0; i < total; i++) {
          const t = Math.round((i / VIDEO_FPS) * 1000);
          await evaluate(
            call,
            `(async () => {
               document.documentElement.style.setProperty('--t', '${t}ms');
               await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
             })()`,
          );
          await shoot(call, path.join(frames, `f-${String(i).padStart(4, '0')}.jpg`), 'jpeg');
          if (i % 60 === 0) process.stdout.write(`  ${name}: ${i}/${total}\r`);
        }

        await run(FFMPEG, [
          '-y',
          '-framerate',
          String(VIDEO_FPS),
          '-i',
          path.join(frames, 'f-%04d.jpg'),
          '-c:v',
          'libx264',
          '-profile:v',
          'high',
          '-level',
          '4.0',
          '-preset',
          'slow',
          '-crf',
          '18',
          // yuv420p: sem isso o Instagram e o QuickTime recusam ou exibem torto.
          '-pix_fmt',
          'yuv420p',
          '-movflags',
          '+faststart',
          path.join(OUT, name),
        ]);
        await rm(frames, { recursive: true, force: true });

        const probe = await validateMp4(FFMPEG, path.join(OUT, name), total);
        const buf = await readFile(path.join(OUT, name));
        manifest.push({ file: name, bytes: buf.length, sha256: sha(buf), stream: probe.stream, frames: probe.frames });
        console.log(
          `✓ ${name} (${(buf.length / 1024 / 1024).toFixed(2)} MB, ${probe.frames} quadros, ` +
            `${((Date.now() - started) / 1000).toFixed(0)}s) — validado`,
        );
      }
    }

  } finally {
    browser.ws.close();
    child.kill('SIGKILL');
    server.close();
    await once(child, 'exit').catch(() => {});
    await rm(profile, { recursive: true, force: true });
  }

  await writeFile(
    path.join(OUT, 'MANIFEST.json'),
    `${JSON.stringify({ width: WIDTH, height: HEIGHT, fps: VIDEO_FPS, restT: REST_T, files: manifest }, null, 2)}\n`,
  );

  const leftovers = (await readdir(OUT)).filter((f) => f.startsWith('.'));
  if (leftovers.length) console.warn(`aviso: sobrou ${leftovers.join(', ')} em out/`);
}

function sha(buf) {
  return createHash('sha256').update(buf).digest('hex').slice(0, 16);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
