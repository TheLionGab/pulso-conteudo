#!/usr/bin/env node
/**
 * BGM + SFX via HeyGen library (510 créditos Creator) — sem quota ElevenLabs Music.
 * Uso: node tools/fetch_heygen_audio_v22.mjs
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  downloadTo,
  heygenAuthHeaders,
  searchSounds,
} from "/Users/mac/.agents/skills/media-use/audio/scripts/lib/heygen.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const BGM_RAW = join(ROOT, "assets/bgm/heygen-track-raw.mp3");
const BGM_OUT = join(ROOT, "assets/bgm/bed-pulso-heygen-v22.mp3");
const SFX_DIR = join(ROOT, "assets/sfx/heygen");

const BGM_QUERY =
  "minimal fintech agriculture app underscore calm confident subtle pulse instrumental no vocals";

const SFX_CUES = [
  { name: "short smooth UI whoosh transition airy modern app", out: "whoosh-short.mp3" },
  { name: "soft premium mobile UI tap click subtle", out: "click-soft.mp3" },
  { name: "soft UI pop notification mobile", out: "pop.mp3" },
  { name: "keyboard typing mobile search field", out: "typing.mp3" },
  { name: "deep soft bass impact price reveal controlled", out: "impact-bass-2.mp3" },
  { name: "short subtle riser app store CTA", out: "riser.mp3" },
  { name: "cinematic bass hit lockup", out: "impact-bass-1.mp3" },
];

function probe(path) {
  const r = spawnSync(
    "ffprobe",
    ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
    { encoding: "utf8" },
  );
  return parseFloat(r.stdout.trim());
}

async function main() {
  const headers = heygenAuthHeaders();
  console.log("HeyGen auth OK");

  const music = await searchSounds(BGM_QUERY, "music", headers, { limit: 8 });
  if (!music.length) throw new Error("HeyGen music: zero results");
  const top = music[0];
  console.log(`BGM hit: ${top.name ?? top.description ?? "?"} score=${top.score}`);
  await downloadTo(top.audio_url, BGM_RAW);

  const rawDur = probe(BGM_RAW);
  const start = rawDur > 28 ? Math.min(8, rawDur * 0.15) : 0;
  spawnSync(
    "ffmpeg",
    [
      "-y",
      "-v",
      "error",
      "-ss",
      String(start),
      "-i",
      BGM_RAW,
      "-t",
      "22",
      "-af",
      "afade=t=in:st=0:d=1.2,afade=t=out:st=19.5:d=2.5,volume=0.55",
      BGM_OUT,
    ],
    { stdio: "inherit" },
  );
  console.log(`BGM → ${BGM_OUT} (${probe(BGM_OUT).toFixed(2)}s)`);

  mkdirSync(SFX_DIR, { recursive: true });
  const manifest = { provider: "heygen", bgm_query: BGM_QUERY, cues: [] };
  for (const cue of SFX_CUES) {
    const hits = await searchSounds(cue.name, "sound_effects", headers, { limit: 3, minScore: 0.4 });
    if (!hits.length) {
      console.warn(`SKIP sfx: ${cue.out}`);
      continue;
    }
    const hit = hits[0];
    const dest = join(SFX_DIR, cue.out);
    await downloadTo(hit.audio_url, dest);
    const dur = probe(dest);
    manifest.cues.push({ file: `assets/sfx/heygen/${cue.out}`, query: cue.name, duration_s: dur, score: hit.score });
    console.log(`SFX ${cue.out} ${dur.toFixed(2)}s score=${hit.score}`);
  }
  writeFileSync(join(SFX_DIR, "manifest.json"), JSON.stringify(manifest, null, 2));
  console.log("DONE");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
