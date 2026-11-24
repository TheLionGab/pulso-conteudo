"""Pergunta ao app (REST só leitura) se já há episódio no dia ou com o mesmo id: evita publicar duas vezes.

Uso: python3 -I ja_publicado.py <AAAA-MM-DD> [<id do episódio>]
Saída: 0 = nada no dia e id livre (pode publicar); 10 = já há episódio publicado no dia (pular, não é erro);
11 = o id já existe no catálogo, em qualquer status (recusar: é decisão humana); 1 = erro (não publicar).
O app só aceita um episódio publicado por dia (publicado_em) e id único; este teste evita descobrir isso no aprovar.
Ambiente: SUPABASE_SERVICE_ROLE_KEY (nunca impressa) e SUPABASE_URL (padrão: projeto do Pulso).
"""
import datetime as dt
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL_PADRAO = "https://jgsmgvplwhisapvuqcji.supabase.co"
ID_RE = re.compile(r"^(?=.{1,80}$)[a-z0-9]+(?:-[a-z0-9]+)*$")  # mesmo contrato do app (publicar.mjs)


def consultar(base, chave, filtro, abrir=urlopen):
    url = f"{base}/rest/v1/pulso_news_episodios?select=id,status&{filtro}&limit=5"
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
    return [(linha["id"], linha["status"]) for linha in linhas]


def publicados_no_dia(dia, base, chave, abrir=urlopen):
    dt.date.fromisoformat(dia)
    return [i for i, _ in consultar(base, chave, f"publicado_em=eq.{dia}&status=eq.publicado", abrir)]


def status_do_id(id_, base, chave, abrir=urlopen):
    if not ID_RE.match(id_):
        raise ValueError(f"id inválido: {id_!r}")
    achados = consultar(base, chave, f"id=eq.{id_}", abrir)
    return achados[0][1] if achados else None


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
    if len(argv) > 1:
        status = status_do_id(argv[1], base, chave)
        if status is not None:
            print(f"o id {argv[1]} já existe no catálogo (status {status}); decisão humana", file=sys.stderr)
            return 11
    print(f"nenhum episódio publicado em {argv[0]} e id livre")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (RuntimeError, ValueError, KeyError, IndexError) as erro:
        print(f"ja_publicado: {erro}", file=sys.stderr)
        sys.exit(1)
