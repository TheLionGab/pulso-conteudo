"""G5: monta out/ep.json (meta do publicar.mjs) e roda `publicar.mjs rascunho --dry-run` como gate.

Uso: python3 -I g5_ep_json.py <pasta_episodio> <video.mp4> <capa.jpg>
Fontes do meta: episodio.json (editorial), dossie.json (id e data) e ffprobe (duração).
Na entrada legada sem episodio.json, mantém a leitura de roteiro.md e dossie.json. O publicar.mjs vem da origin/main do Pulso
(`git show`, sem tocar na árvore de ninguém). O dry-run não usa chave nem rede e não sobe nada.
Código 1 se o meta não montar ou o dry-run reprovar.
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

EP, VIDEO, CAPA = (os.path.abspath(a) for a in sys.argv[1:4])
REPO = os.environ.get("PULSO_APP_REPO", str(Path.home() / "Developer/Pulso-Do-Campo"))
dossie = json.load(open(os.path.join(EP, "dossie.json"), encoding="utf-8"))
entrada = Path(EP) / "episodio.json"
episodio = json.loads(entrada.read_text()) if entrada.is_file() else None
md = "" if episodio else (Path(EP) / "roteiro.md").read_text()


def campo_push(rotulo):
    m = re.search(rf"^- {rotulo} \(≤ \d+\): (.+?)(?=\n- |\n\n|\Z)", md, re.M | re.S)
    if not m:
        sys.exit(f"G5 reprovado: roteiro.md sem '- {rotulo} (≤ N): ...' na seção Push")
    return " ".join(m.group(1).split())


titulo = re.search(r'^# .*?"([^"]+)"', md, re.M)
if not episodio and not titulo:
    sys.exit('G5 reprovado: o H1 do roteiro.md não traz o título entre aspas')

por_url = {}  # uma fonte por URL; o nome mais curto entre as linhas que a citam
for l in [] if episodio else dossie["linhas"]:
    url = l.get("url") or l.get("fonte_url")
    if not url:
        sys.exit(f"G5 reprovado: linha {l['id']} sem url nem fonte_url")
    atual = por_url.get(url)
    if atual is None or len(l["fonte_primaria"]) < len(atual["nome"]):
        por_url[url] = {"nome": l["fonte_primaria"], "url": url, "data": l["data_publicacao"]}
fontes = list(por_url.values())

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                           capture_output=True, text=True, check=True).stdout)
meta = {
    "id": dossie["episodio"],
    "titulo": episodio["titulo"] if episodio else titulo.group(1),
    "resumo": episodio["resumo"] if episodio else dossie["tese"],
    "publicado_em": dossie["data"],
    "duracao_seg": round(dur),
    "push_titulo": episodio["push"]["titulo"] if episodio else campo_push("Título"),
    "push_corpo": episodio["push"]["corpo"] if episodio else campo_push("Corpo"),
    "fontes": episodio["fontes"] if episodio else fontes,
}
destino = os.path.join(EP, "out/ep.json")

with tempfile.TemporaryDirectory() as tmp:
    # Caminho real: o publicar.mjs só executa quando argv[1] é igual ao import.meta.url, e o
    # temporário do macOS (/var -> /private/var) é link simbólico; sem isso o node sai 0 calado.
    script = os.path.join(os.path.realpath(tmp), "publicar.mjs")
    src = subprocess.run(["git", "-C", REPO, "show", "origin/main:scripts/pulso-news/publicar.mjs"],
                         capture_output=True, text=True)
    if src.returncode != 0:
        sys.exit(f"G5 reprovado: não li o publicar.mjs da origin/main ({src.stderr.strip()[:120]})")
    open(script, "w").write(src.stdout)
    # publicar.mjs importa frescor.mjs (G6) da mesma pasta.
    fr = subprocess.run(["git", "-C", REPO, "show", "origin/main:scripts/pulso-news/frescor.mjs"],
                        capture_output=True, text=True)
    if fr.returncode != 0:
        sys.exit(f"G5 reprovado: não li o frescor.mjs da origin/main ({fr.stderr.strip()[:120]})")
    open(os.path.join(os.path.dirname(script), "frescor.mjs"), "w").write(fr.stdout)
    meta_app = os.path.join(os.path.dirname(script), "ep.json")
    with open(meta_app, "w", encoding="utf-8") as saida:
        json.dump(meta, saida, ensure_ascii=False)
    node = shutil.which("node")
    if node is None:
        sys.exit("G5 reprovado: Node não está no PATH")
    r = subprocess.run([node, script, "rascunho", "--meta", meta_app, "--video", VIDEO, "--capa", CAPA,
                        "--dossie", os.path.join(EP, "dossie.json"), "--dry-run"],
                       capture_output=True, text=True, env={"PATH": os.defpath})
print((r.stdout + r.stderr).strip())
if r.returncode != 0 or "Validação OK (dry-run" not in r.stdout:
    sys.exit(f"G5 reprovado: publicar.mjs --dry-run saiu com {r.returncode} sem 'Validação OK'")
with open(destino, "w", encoding="utf-8") as saida:
    json.dump(meta, saida, ensure_ascii=False, indent=2)
if episodio:
    (Path(EP) / "out/legenda-instagram.txt").write_text(episodio["legenda_instagram"].strip() + "\n", encoding="utf-8")
print(f"G5 aprovado: {destino} validado pelo publicar.mjs (dry-run, nada enviado)")
