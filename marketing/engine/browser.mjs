// Chromium headless via CDP cru, sem dependência de npm.
//
// Por que não Playwright: instalar `playwright` mexeria no lockfile do monorepo
// por causa de peça de marketing, e o Chromium já vem na imagem. O que se usa
// aqui é meia dúzia de comandos CDP.

import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { existsSync } from 'node:fs';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

export const CHROMIUM = firstExisting([
  process.env.CHROMIUM_PATH,
  '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  '/opt/pw-browsers/chromium/chrome-linux/chrome',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/chromium',
]);

export function firstExisting(candidates) {
  for (const c of candidates) if (c && existsSync(c)) return c;
  return null;
}

/**
 * Flags fixas por um motivo: determinismo. Sem hinting e sem posicionamento
 * subpixel, o mesmo HTML no mesmo instante gera o mesmo PNG em qualquer
 * máquina — é o que torna o diff de uma arte auditável e o que permite provar
 * que um refactor do motor não mexeu em nenhum pixel.
 *
 * Mudar qualquer flag daqui muda o sha256 de TODAS as peças já renderizadas.
 */
const DETERMINISM_FLAGS = [
  '--force-device-scale-factor=1',
  '--font-render-hinting=none',
  '--disable-font-subpixel-positioning',
  '--disable-lcd-text',
];

export async function launchChromium() {
  if (!CHROMIUM) throw new Error('Chromium não encontrado. Defina CHROMIUM_PATH.');

  // Perfil em tmp, nunca dentro de out/: o Chromium ainda está gravando quando
  // o script termina, e apagar a pasta no finally dava ENOTEMPTY.
  const profile = await mkdtemp(path.join(os.tmpdir(), 'pdc-marketing-'));

  const child = spawn(
    CHROMIUM,
    [
      '--headless=new',
      '--remote-debugging-port=0',
      '--no-sandbox',
      '--disable-gpu',
      '--hide-scrollbars',
      ...DETERMINISM_FLAGS,
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

  const browser = await Cdp.connect(wsUrl);

  return {
    browser,
    async close() {
      browser.ws.close();
      child.kill('SIGKILL');
      await once(child, 'exit').catch(() => {});
      await rm(profile, { recursive: true, force: true });
    },
  };
}

/** Cliente CDP mínimo sobre o WebSocket nativo do Node 22. */
export class Cdp {
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

/** Aba dimensionada para um formato (`{ width, height }`). */
export async function openPage(browser, { width, height }) {
  const { targetId } = await browser.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await browser.send('Target.attachToTarget', { targetId, flatten: true });
  const call = (method, params) => browser.send(method, params, sessionId);

  await call('Page.enable');
  await call('Runtime.enable');
  await call('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
  });

  return new Page(call, width, height);
}

export class Page {
  constructor(call, width, height) {
    this.call = call;
    this.width = width;
    this.height = height;
  }

  async evaluate(expression) {
    const { result, exceptionDetails } = await this.call('Runtime.evaluate', {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });
    if (exceptionDetails) throw new Error(exceptionDetails.text ?? 'erro no page script');
    return result.value;
  }

  /**
   * Navega e só devolve quando a página sinalizou `data-ready`. Screenshot antes
   * disso captura fallback de fonte — métrica diferente, quebra de linha
   * diferente, e ninguém percebe até a arte estar publicada.
   */
  async goto(url) {
    await this.call('Page.navigate', { url });
    const deadline = Date.now() + 20_000;
    for (;;) {
      const ready = await this.evaluate('document.documentElement.dataset.ready === "1"').catch(() => false);
      if (ready) break;
      if (Date.now() > deadline) throw new Error(`página não ficou pronta: ${url}`);
      await new Promise((r) => setTimeout(r, 50));
    }
    await this.settle();
  }

  /** Dois rAF: garante que o estilo já entrou em um frame composto. */
  settle() {
    return this.evaluate('new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))');
  }

  /** Move a animação congelada para o instante `t` (ms) sem recarregar a página. */
  async seek(t) {
    await this.evaluate(
      `(async () => {
         document.documentElement.style.setProperty('--t', '${Math.round(t)}ms');
         await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
       })()`,
    );
  }

  /**
   * `format`: PNG para arte final; JPEG q=95 para quadros intermediários de
   * vídeo. Codificar 500 PNGs de 1080x1920 dominava o tempo de render e o ganho
   * é invisível depois do H.264.
   */
  async shoot(file, format = 'png') {
    const { data } = await this.call('Page.captureScreenshot', {
      format,
      ...(format === 'jpeg' ? { quality: 95 } : {}),
      captureBeyondViewport: false,
      clip: { x: 0, y: 0, width: this.width, height: this.height, scale: 1 },
    });
    const buf = Buffer.from(data, 'base64');
    await writeFile(file, buf);
    return buf;
  }
}
