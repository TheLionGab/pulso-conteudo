"""Baixa o acervo do bucket privado pulso-acervo (Supabase do Pulso) para uma pasta local.

Uso: python3 -I baixar_acervo.py <pasta_acervo>
Cada item do manifest.json fica em <pasta_acervo>/<origem> (o mesmo caminho do acervo do iCloud) e só
vale com o sha256 do manifesto: item já presente e íntegro é pulado (cache do CI), o resto é baixado
para um temporário, conferido e só então renomeado. Depois, PULSO_ACERVO=<pasta_acervo> e
assets/integridade.py obter confere de novo ao copiar para o trabalho.
Ambiente: SUPABASE_SERVICE_ROLE_KEY (nunca impressa) e SUPABASE_URL (padrão: projeto do Pulso).
"""
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

URL_PADRAO = "https://jgsmgvplwhisapvuqcji.supabase.co"
MANIFESTO = Path(__file__).with_name("manifest.json")
BUCKET = "pulso-acervo"


def sha256_arquivo(caminho):
    with open(caminho, "rb") as entrada:
        return hashlib.file_digest(entrada, "sha256").hexdigest()


def destino_seguro(acervo, origem):
    caminho = Path(origem)
    if caminho.is_absolute() or ".." in caminho.parts or not caminho.parts:
        raise ValueError(f"origem fora do acervo: {origem}")
    return acervo / caminho


def baixar_item(base, chave, acervo, item, tentativas=3):
    alvo = destino_seguro(acervo, item["origem"])
    if alvo.is_file() and sha256_arquivo(alvo) == item["sha256"]:
        return "cache"
    alvo.parent.mkdir(parents=True, exist_ok=True)
    pedido = Request(f"{base}/storage/v1/object/{BUCKET}/{quote(item['origem'], safe='/')}",
                     headers={"Authorization": f"Bearer {chave}", "apikey": chave})
    ultimo = ""
    for n in range(tentativas):
        with tempfile.NamedTemporaryFile(dir=alvo.parent, delete=False) as tmp:
            temporario = Path(tmp.name)
        try:
            with urlopen(pedido, timeout=300) as resposta, open(temporario, "wb") as saida:
                while bloco := resposta.read(1 << 20):
                    saida.write(bloco)
            if sha256_arquivo(temporario) != item["sha256"]:
                raise ValueError("sha256 diferente do manifesto")
            temporario.replace(alvo)
            return "baixado"
        except HTTPError as e:  # sem cabeçalho no erro: a chave não vaza
            ultimo = f"HTTP {e.code}"
            if 400 <= e.code < 500 and e.code != 429:
                break
        except (URLError, TimeoutError, OSError, ValueError) as e:
            ultimo = str(e) if isinstance(e, ValueError) else type(e).__name__
        finally:
            temporario.unlink(missing_ok=True)
        if n + 1 < tentativas:
            time.sleep(5 * (n + 1))
    raise RuntimeError(f"{item['origem']}: {ultimo}")


def main(argv):
    acervo = Path(argv[0]).resolve()
    chave = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not chave:
        raise RuntimeError("falta SUPABASE_SERVICE_ROLE_KEY")
    base = os.environ.get("SUPABASE_URL", URL_PADRAO).strip().rstrip("/")
    if not base.startswith("https://"):
        raise RuntimeError("SUPABASE_URL tem de ser https")
    itens = json.loads(MANIFESTO.read_text())
    contagem = {"cache": 0, "baixado": 0}
    for item in itens.values():
        contagem[baixar_item(base, chave, acervo, item)] += 1
    print(f"acervo ok: {len(itens)} itens ({contagem['cache']} do cache, {contagem['baixado']} baixados do bucket)")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (RuntimeError, ValueError, OSError, IndexError) as erro:
        sys.exit(f"baixar_acervo: {erro}")
