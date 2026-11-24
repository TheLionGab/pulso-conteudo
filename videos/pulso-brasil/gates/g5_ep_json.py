"""G5: monta out/ep.json (meta do publicar.mjs) e roda `publicar.mjs rascunho --dry-run` como gate.

Uso: python3 -I g5_ep_json.py <pasta_episodio> <video.mp4> <capa.jpg>
Fontes do meta: dossie.json (id, data, tese, fontes), roteiro.md (título no H1 entre aspas,
push na seção "## Push") e ffprobe (duração). O publicar.mjs vem da origin/main do Pulso
(`git show`, sem tocar na árvore de ninguém). O dry-run não usa chave nem rede e não sobe nada.
Código 1 se o meta não montar ou o dry-run reprovar.
"""
import json, os, re, subprocess, sys, tempfile

EP, VIDEO, CAPA = (os.path.abspath(a) for a in sys.argv[1:4])
REPO = "/Users/mac/Developer/Pulso-Do-Campo"
dossie = json.load(open(os.path.join(EP, "dossie.json"), encoding="utf-8"))
md = open(os.path.join(EP, "roteiro.md"), encoding="utf-8").read()


def campo_push(rotulo):
    m = re.search(rf"^- {rotulo} \(≤ \d+\): (.+?)(?=\n- |\n\n|\Z)", md, re.M | re.S)
    if not m:
        sys.exit(f"G5 reprovado: roteiro.md sem '- {rotulo} (≤ N): ...' na seção Push")
    return " ".join(m.group(1).split())


titulo = re.search(r'^# .*?"([^"]+)"', md, re.M)
if not titulo:
    sys.exit('G5 reprovado: o H1 do roteiro.md não traz o título entre aspas')

por_url = {}  # uma fonte por URL; o nome mais curto entre as linhas que a citam
for l in dossie["linhas"]:
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
    "titulo": titulo.group(1),
    "resumo": dossie["tese"],
    "publicado_em": dossie["data"],
    "duracao_seg": round(dur),
    "push_titulo": campo_push("Título"),
    "push_corpo": campo_push("Corpo"),
    "fontes": fontes,
}
destino = os.path.join(EP, "out/ep.json")
json.dump(meta, open(destino, "w"), ensure_ascii=False, indent=2)

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
    env = {k: v for k, v in os.environ.items() if not k.startswith("SUPABASE")}
    r = subprocess.run(["node", script, "rascunho", "--meta", destino, "--video", VIDEO, "--capa", CAPA,
                        "--dossie", os.path.join(EP, "dossie.json"), "--dry-run"],
                       capture_output=True, text=True, env=env)
print((r.stdout + r.stderr).strip())
if r.returncode != 0 or "Validação OK (dry-run" not in r.stdout:
    sys.exit(f"G5 reprovado: publicar.mjs --dry-run saiu com {r.returncode} sem 'Validação OK'")
print(f"G5 aprovado: {destino} validado pelo publicar.mjs (dry-run, nada enviado)")
