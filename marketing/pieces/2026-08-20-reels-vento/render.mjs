#!/usr/bin/env node
// Renderiza o Reels (1080x1920, 18s, H.264) a partir de index.html.
//
// Saída em out/: reels-vento.mp4 + capa.png + MANIFEST.json
//
// Uso: node marketing/pieces/2026-08-20-reels-vento/render.mjs

import { createHash } from 'node:crypto';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { launchChromium, openPage } from '../../engine/browser.mjs';
import { assertH264, encodeMp4, validateMp4, FFMPEG } from '../../engine/encode.mjs';
import { serve } from '../../engine/serve.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'out');

const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;
const DURATION_MS = 18_200;
/** Instante usado como capa: meio da primeira cena, já totalmente revelada. */
const COVER_T = 2400;

/**
 * Gate de safe area do Reels. Diferente do Stories: legenda e botões comem
 * ~480px embaixo e a coluna de ações ~200px à direita. Texto fora da caixa
 * fica atrás da UI do Instagram e ninguém percebe até publicar.
 */
async function assertScenesFit(page) {
  const problems = await page.evaluate(
    `(() => {
       const safe = document.querySelector('.safe').getBoundingClientRect();
       const out = [];
       document.querySelectorAll('.scene').forEach((scene, i) => {
         const r = scene.getBoundingClientRect();
         if (r.height > safe.height) out.push('cena ' + (i + 1) + ' tem ' + Math.round(r.height) + 'px, safe area tem ' + Math.round(safe.height));
         scene.querySelectorAll('*').forEach((el) => {
           const b = el.getBoundingClientRect();
           if (b.width && b.right > safe.right + 1) out.push('cena ' + (i + 1) + ': elemento vaza ' + Math.round(b.right - safe.right) + 'px à direita');
         });
       });
       return [...new Set(out)];
     })()`,
  );
  if (problems.length) throw new Error(`safe area do Reels:\n  - ${problems.join('\n  - ')}`);
}

function sha(buf) {
  return createHash('sha256').update(buf).digest('hex').slice(0, 16);
}

async function main() {
  await assertH264();

  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });
  const frames = path.join(OUT, '.frames');
  await mkdir(frames, { recursive: true });

  const server = await serve(HERE);
  const { browser, close } = await launchChromium();
  const manifest = [];

  try {
    const page = await openPage(browser, { width: WIDTH, height: HEIGHT });
    await page.goto(server.url({ t: 0 }));
    await assertScenesFit(page);

    const total = Math.round((DURATION_MS / 1000) * FPS);
    const started = Date.now();

    for (let i = 0; i < total; i++) {
      await page.seek((i / FPS) * 1000);
      await page.shoot(path.join(frames, `f-${String(i).padStart(4, '0')}.jpg`), 'jpeg');
      if (i % 90 === 0) process.stdout.write(`  quadros ${i}/${total}\r`);
    }
    console.log(`  quadros ${total}/${total} em ${((Date.now() - started) / 1000).toFixed(0)}s`);

    // Capa: o Instagram deixa escolher o quadro de capa, mas exportar o PNG
    // separado evita depender do seletor de capa do app (que recomprime).
    await page.seek(COVER_T);
    const cover = await page.shoot(path.join(OUT, 'capa.png'));
    manifest.push({ file: 'capa.png', bytes: cover.length, sha256: sha(cover) });

    const mp4 = path.join(OUT, 'reels-vento.mp4');
    await encodeMp4({ framesGlob: path.join(frames, 'f-%04d.jpg'), fps: FPS, out: mp4 });
    await rm(frames, { recursive: true, force: true });

    const probe = await validateMp4({ file: mp4, expectedFrames: total, width: WIDTH, height: HEIGHT, fps: FPS });
    const buf = await readFile(mp4);
    manifest.push({
      file: 'reels-vento.mp4',
      bytes: buf.length,
      sha256: sha(buf),
      stream: probe.stream,
      frames: probe.frames,
      durationSeconds: total / FPS,
    });
    console.log(
      `✓ reels-vento.mp4 (${(buf.length / 1024 / 1024).toFixed(2)} MB, ${probe.frames} quadros, ` +
        `${(total / FPS).toFixed(1)}s) — validado`,
    );
  } finally {
    await close();
    server.close();
  }

  await writeFile(
    path.join(OUT, 'MANIFEST.json'),
    `${JSON.stringify({ width: WIDTH, height: HEIGHT, fps: FPS, ffmpeg: FFMPEG, files: manifest }, null, 2)}\n`,
  );
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
