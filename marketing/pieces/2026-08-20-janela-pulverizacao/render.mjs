#!/usr/bin/env node
// Renderiza o carrossel de feed (1080x1350, 7 slides) a partir de index.html.
//
// Saída em out/: slide-1.png .. slide-7.png + MANIFEST.json
//
// Uso: node marketing/pieces/2026-08-20-janela-pulverizacao/render.mjs

import { createHash } from 'node:crypto';
import { mkdir, readdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { launchChromium, openPage } from '../../engine/browser.mjs';
import { serve } from '../../engine/serve.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'out');

const WIDTH = 1080;
const HEIGHT = 1350;
const SLIDES = 7;

/**
 * Gate de layout do carrossel. Slide que transborda o quadro sai cortado no
 * Instagram e ninguém percebe até estar publicado — e num carrossel o estrago
 * é pior, porque só um dos sete quebra e passa despercebido na revisão.
 */
async function assertFits(page, label) {
  const box = await page.evaluate(
    `(() => {
       const c = document.querySelector('.content');
       const h1 = document.querySelector('h1');
       return {
         overflow: c.scrollHeight - c.clientHeight,
         wide: Math.max(0, h1.scrollWidth - h1.clientWidth),
         lines: h1.querySelectorAll('.line').length,
         h1Height: Math.round(h1.getBoundingClientRect().height),
         fontSize: parseFloat(getComputedStyle(h1).fontSize),
         lineHeight: parseFloat(getComputedStyle(h1).lineHeight),
       };
     })()`,
  );

  const problems = [];
  if (box.overflow > 0) problems.push(`conteúdo vaza ${box.overflow}px do quadro`);
  if (box.wide > 0) problems.push(`título vaza ${box.wide}px na horizontal`);

  // Cada .line tem que ocupar exatamente uma linha renderizada. Se o navegador
  // quebrou uma delas por conta própria, o ritmo do bloco muda e o slide
  // desalinha do resto do carrossel.
  const expected = Math.round(box.lines * box.lineHeight);
  if (box.h1Height > expected + 4) {
    problems.push(`título quebrou linha extra (${box.h1Height}px > ${expected}px para ${box.lines} linhas)`);
  }

  if (problems.length) throw new Error(`${label}: ${problems.join(' · ')}`);
}

function sha(buf) {
  return createHash('sha256').update(buf).digest('hex').slice(0, 16);
}

async function main() {
  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });

  const server = await serve(HERE);
  const { browser, close } = await launchChromium();
  const manifest = [];

  try {
    const page = await openPage(browser, { width: WIDTH, height: HEIGHT });

    for (let slide = 1; slide <= SLIDES; slide++) {
      const name = `slide-${slide}.png`;
      await page.goto(server.url({ slide }));
      await assertFits(page, name);
      const buf = await page.shoot(path.join(OUT, name));
      manifest.push({ file: name, bytes: buf.length, sha256: sha(buf) });
      console.log(`✓ ${name} (${(buf.length / 1024).toFixed(0)} kB)`);
    }
  } finally {
    await close();
    server.close();
  }

  await writeFile(
    path.join(OUT, 'MANIFEST.json'),
    `${JSON.stringify({ width: WIDTH, height: HEIGHT, slides: SLIDES, files: manifest }, null, 2)}\n`,
  );

  const leftovers = (await readdir(OUT)).filter((f) => f.startsWith('.'));
  if (leftovers.length) console.warn(`aviso: sobrou ${leftovers.join(', ')} em out/`);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
