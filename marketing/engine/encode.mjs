// Encode e validação de MP4 para Instagram (Reels, Stories, feed).

import { spawn } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { firstExisting } from './browser.mjs';

// Ordem importa: o ffmpeg que vem com o Playwright é uma build mínima (só
// VP8/WebM, sem libx264) e o Instagram não aceita WebM. Um ffmpeg completo do
// sistema tem que vir antes, senão o render vai longe e morre no fim.
export const FFMPEG = firstExisting([
  process.env.FFMPEG_PATH,
  '/opt/homebrew/bin/ffmpeg',
  '/usr/local/bin/ffmpeg',
  '/usr/bin/ffmpeg',
]);

/** Confere que o ffmpeg escolhido encoda H.264 ANTES de gastar minutos de render. */
export async function assertH264(bin = FFMPEG) {
  if (!bin) throw new Error('ffmpeg não encontrado. Defina FFMPEG_PATH.');
  const out = await capture(bin, ['-hide_banner', '-encoders']);
  if (!out.includes('libx264')) {
    throw new Error(
      `ffmpeg em ${bin} não tem libx264 — o MP4 do Instagram exige H.264.\n` +
        'Instale um ffmpeg completo (macOS: brew install ffmpeg) ou aponte FFMPEG_PATH para ele.',
    );
  }
}

function capture(bin, args) {
  return new Promise((resolve, reject) => {
    const p = spawn(bin, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let buf = '';
    p.stdout.on('data', (d) => (buf += d));
    p.stderr.on('data', (d) => (buf += d));
    p.on('error', reject);
    p.on('exit', () => resolve(buf));
  });
}

export function run(bin, args) {
  return new Promise((resolve, reject) => {
    const p = spawn(bin, args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let err = '';
    p.stderr.on('data', (d) => (err += d));
    p.on('exit', (code) =>
      code === 0 ? resolve() : reject(new Error(`${path.basename(bin)} falhou (${code}):\n${err.slice(-1500)}`)),
    );
  });
}

/**
 * Sequência de quadros → MP4 que o Instagram aceita.
 *
 * `yuv420p` e `+faststart` não são preferência: sem o primeiro o app recusa ou
 * exibe torto; sem o segundo o player precisa do arquivo inteiro antes de
 * começar — que é o que trava upload em conexão de campo.
 */
export async function encodeMp4({ framesGlob, fps, out, bin = FFMPEG }) {
  await run(bin, [
    '-y',
    '-framerate',
    String(fps),
    '-i',
    framesGlob,
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
    '-pix_fmt',
    'yuv420p',
    '-movflags',
    '+faststart',
    out,
  ]);
}

/**
 * Valida o MP4 decodificando o arquivo INTEIRO. Conferir tamanho não prova
 * nada: um MP4 truncado abre no Finder e só falha na hora do upload.
 */
export async function validateMp4({ file, expectedFrames, width, height, fps, bin = FFMPEG }) {
  const log = await capture(bin, ['-hide_banner', '-i', file, '-f', 'null', '-']);
  const stream = log.match(/Stream #0:0.*Video: (.+)/)?.[1] ?? '';

  const problems = [];
  if (!/\bh264\b/.test(stream)) problems.push(`codec não é H.264: ${stream || '(sem stream de vídeo)'}`);
  if (!stream.includes('yuv420p')) problems.push('pix_fmt não é yuv420p (o Instagram recusa)');
  if (!stream.includes(`${width}x${height}`)) problems.push(`dimensão errada: esperado ${width}x${height}`);
  if (!stream.includes(`${fps} fps`)) problems.push(`fps errado: esperado ${fps}`);
  if (/Audio:/.test(log)) problems.push('faixa de áudio inesperada');

  const decoded = Number([...log.matchAll(/frame=\s*(\d+)/g)].at(-1)?.[1] ?? 0);
  if (decoded !== expectedFrames) problems.push(`decodificou ${decoded} quadros, esperado ${expectedFrames}`);

  // faststart: moov antes do mdat.
  const head = await readFile(file);
  const moov = head.indexOf('moov');
  const mdat = head.indexOf('mdat');
  if (moov < 0 || mdat < 0 || moov > mdat) problems.push('sem faststart (moov depois do mdat)');

  if (problems.length) throw new Error(`${path.basename(file)} inválido:\n  - ${problems.join('\n  - ')}`);
  return { stream: stream.trim(), frames: decoded, bytes: head.length };
}
