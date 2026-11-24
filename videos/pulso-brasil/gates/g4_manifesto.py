"""G4: confere o mp4 e a capa e grava out/manifesto.json. Sem rede, sem chave.

Uso: python3 -I g4_manifesto.py <pasta_episodio> <video.mp4> <capa.jpg>
Reprova (código 1, sem gravar) se: vídeo não for h264 1080x1920 com áudio aac; duração diferir
da timeline em mais de 0,5 s; `ffmpeg -f null` acusar erro de decodificação; loudness integrado
fora de -14 ± 1 LUFS ou pico acima de -1 dBTP; capa não for jpeg 1080x1920.
Também exige 30 fps, 30–60 s, fecho_app, legenda e a voz canônica.
"""
import datetime, hashlib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
from g_forma import checar as forma
from g_voz import checar as voz

EP, VIDEO, CAPA = (os.path.abspath(a) for a in sys.argv[1:4])
falhas = []


def sha(p):
    with open(p, "rb") as entrada:
        return hashlib.file_digest(entrada, "sha256").hexdigest()


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate:format=duration",
                        "-of", "json", p], capture_output=True, text=True)
    return json.loads(r.stdout or "{}") if r.returncode == 0 else {}


v = probe(VIDEO)
vs = [s for s in v.get("streams", []) if s.get("codec_type") == "video"]
aus = [s for s in v.get("streams", []) if s.get("codec_type") == "audio"]
if not vs or (vs[0].get("codec_name"), vs[0].get("width"), vs[0].get("height")) != ("h264", 1080, 1920):
    falhas.append(f"vídeo não é h264 1080x1920: {vs[:1]}")
if not aus or aus[0].get("codec_name") != "aac":
    falhas.append(f"áudio não é aac: {aus[:1]}")
dur = float(v.get("format", {}).get("duration", 0))
tl = json.load(open(os.path.join(EP, "video/public/timeline.json")))
if abs(dur - tl["duracao"]) > 0.5:
    falhas.append(f"duração {dur:.2f} s difere da timeline {tl['duracao']:.2f} s")
dec = subprocess.run(["ffmpeg", "-v", "error", "-i", VIDEO, "-f", "null", "-"], capture_output=True, text=True)
if dec.returncode != 0 or dec.stderr.strip():
    falhas.append(f"decodificação com erro: {dec.stderr.strip()[:200]}")

eb = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", VIDEO, "-af",
                     "ebur128=peak=true:framelog=verbose", "-f", "null", "-"],
                    capture_output=True, text=True)
m = re.search(r"Integrated loudness:\s+I:\s+(-?[\d.]+) LUFS", eb.stderr)
tp = re.search(r"True peak:\s+Peak:\s+(-?[\d.]+) dBFS", eb.stderr)
lufs = float(m.group(1)) if m and eb.returncode == 0 else None
pico = float(tp.group(1)) if tp and eb.returncode == 0 else None
with open(os.path.join(EP, "episodio.json"), encoding="utf-8") as entrada:
    episodio = json.load(entrada)
falhas.extend(forma(vs[0] if vs else {}, dur, lufs, pico, episodio))
with open(os.path.join(EP, "audio/sintese.json"), encoding="utf-8") as entrada:
    sintese = json.load(entrada)
try:
    canon = voz(sintese)
except ValueError as erro:
    falhas.append(str(erro))
else:
    if tl.get("voz") != f"{canon['modelo']}/{canon['voz']}":
        falhas.append("timeline não usa a voz canônica")

c = probe(CAPA)
cs = c.get("streams", [{}])[0] if c.get("streams") else {}
if (cs.get("codec_name"), cs.get("width"), cs.get("height")) != ("mjpeg", 1080, 1920):
    falhas.append(f"capa não é jpeg 1080x1920: {cs}")

if falhas:
    for f in falhas:
        print(f"FALHA {f}", file=sys.stderr)
    sys.exit(f"G4 reprovado: {len(falhas)} falha(s); manifesto não gravado")

entradas = ["episodio.json", "dossie.json", "audio/roteiro.json", "audio/sintese.json", "video/public/timeline.json",
            "video/public/mix.m4a"]
manifesto = {
    "episodio": os.path.basename(EP),
    "gerado_em": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "voz": {k: sintese.get(k) for k in ("provedor", "modelo", "voz")},
    "video": {"arquivo": os.path.relpath(VIDEO, EP), "sha256": sha(VIDEO), "bytes": os.path.getsize(VIDEO),
              "duracao_s": round(dur, 3), "largura": 1080, "altura": 1920, "lufs_integrado": lufs, "pico_dbtp": pico, "fps": 30},
    "capa": {"arquivo": os.path.relpath(CAPA, EP), "sha256": sha(CAPA), "bytes": os.path.getsize(CAPA)},
    "entradas_sha256": {e: sha(os.path.join(EP, e)) for e in entradas if os.path.isfile(os.path.join(EP, e))},
    "gates": ["G1 dossiê", "G2 fala", "G3 ASR", "G4 mídia", "g_voz", "g_repeticao"],
}
destino = os.path.join(EP, "out/manifesto.json")
json.dump(manifesto, open(destino, "w"), ensure_ascii=False, indent=2)
print(f"G4 aprovado: {dur:.2f} s, {lufs} LUFS, capa ok; manifesto em {destino}")
