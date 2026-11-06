---
name: pulso-publicar
description: Publicação assistida e retomada de episódios Pulso News aprovados no Instagram e catálogo do app, com preflight local e reconciliação contra duplicatas. Não gera vídeos nem configura agendas.
---

# Publicar Pulso News

Uma solicitação autorizada pode cobrir os dois canais. Reutilize autorização do chat;
recibo, manifesto ou esta skill não autorizam publicação. Não altere agenda, modo
aprovar, guards, voz ou modelo. O helper é local: não publica nem executa SQL.

## Preflight e retomada

Execute da pasta desta skill:

```bash
python3 scripts/workflow.py /caminho/do/episodio
```

Confere hashes do vídeo, capa (quando presente), entradas do manifesto e aprovação
de publicação vinculada ao vídeo. Para publicar, capa e todos os gates do pipeline
têm de existir e estar aprovados no candidato; o manifesto sozinho não os prova.
Recibos completos eliminam ações pendentes, mas são prova histórica local, não
reconferência atual dos canais. Falha no preflight interrompe a ação afetada.
`verify_*` significa inspecionar o canal, não permissão para enviar novamente.

Leia [o procedimento dos canais](references/canais.md) quando houver ação pendente.
Se não houver pendência, relate os recibos existentes e não republice.

## Verificação do helper

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
```

SQL gerado por `insert_sql` é apenas proposta idempotente. Antes de executá-lo,
confirme conta/projeto, schema real, autorização, backup e mídia pública conforme
as regras do app. Não introduza credenciais ou SDK para automatizar este fluxo.
