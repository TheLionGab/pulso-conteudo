"""Pergunta ao app (REST só leitura) se já há episódio publicado no dia: evita publicar duas vezes.

Uso: python3 -I ja_publicado.py <AAAA-MM-DD>
Saída: 0 = nenhum episódio publicado no dia (pode publicar); 10 = já há (não publicar); 1 = erro (não publicar).
O app só aceita um episódio publicado por dia (publicado_em); este teste evita chegar ao aprovar para descobrir.
Ambiente: SUPABASE_SERVICE_ROLE_KEY (nunca impressa) e SUPABASE_URL (padrão: projeto do Pulso).
"""
import datetime as dt
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL_PADRAO = "https://jgsmgvplwhisapvuqcji.supabase.co"


def publicados_no_dia(dia, base, chave, abrir=urlopen):
    dt.date.fromisoformat(dia)
    url = f"{base}/rest/v1/pulso_news_episodios?select=id,status&publicado_em=eq.{dia}&status=eq.publicado&limit=5"
    pedido = Request(url, headers={"apikey": chave, "Authorization": f"Bearer {chave}", "Accept": "application/json"})
    try:
        with abrir(pedido, timeout=30) as resposta:
            linhas = json.loads(resposta.read())
    except HTTPError as erro:  # sem cabeçalhos no erro: a chave não vaza
        raise RuntimeError(f"HTTP {erro.code} ao consultar o catálogo") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("catálogo do app indisponível") from None
    if not isinstance(linhas, list):
        raise RuntimeError("resposta inesperada do catálogo")
    return [linha["id"] for linha in linhas]


def main(argv):
    chave = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not chave:
        raise RuntimeError("falta SUPABASE_SERVICE_ROLE_KEY")
    base = os.environ.get("SUPABASE_URL", URL_PADRAO).strip().rstrip("/")
    if not base.startswith("https://"):
        raise RuntimeError("SUPABASE_URL tem de ser https")
    ids = publicados_no_dia(argv[0], base, chave)
    if ids:
        print(f"já publicado em {argv[0]}: {', '.join(ids)}")
        return 10
    print(f"nenhum episódio publicado em {argv[0]}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (RuntimeError, ValueError, KeyError, IndexError) as erro:
        print(f"ja_publicado: {erro}", file=sys.stderr)
        sys.exit(1)
