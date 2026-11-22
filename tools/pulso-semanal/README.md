# Especial de domingo — Pulso News

Apuração da semana em fontes primárias → seleção de duas ou três decisões úteis a
produtores de MT → pauta estruturada → voz + vídeo vertical → pacote local para
revisão. Sem envio ao Instagram, alteração do catálogo ou push. O diário segue
independente.

- `domingo.py`: entrada da rotina local. Só roda no domingo de MT, previne
  concorrência e não refaz um pacote íntegro. A pesquisa usa a sessão nativa do
  Codex já disponível, web ao vivo e execução somente leitura. A pauta passa
  por validação de estrutura e por uma segunda sessão de conferência factual. Se
  o parecer rejeitar um fato, há uma reapuração seguida de nova conferência.
  Em falha, a rotina sai com erro e não entrega a edição como pronta.
- `render.py`: render local, inclusive para pauta apurada manualmente.
  O manifesto registra voz, SHA-256 do vídeo, duração e verificações mecânicas.
  Uma fonte presente no JSON não é prova de apuração: a revisão editorial humana
  continua antes de qualquer distribuição.
- `domingo.py` também passa ao apurador as edições diárias publicadas no app na
  semana (lidas pelo Supabase CLI), como pistas do que mais pesou; cada fato
  continua reconfirmado na fonte primária. No fim, prepara `meta-app.json`.
- `app.py`: `preparar` gera o meta do app e valida no `publicar.mjs --dry-run`;
  `publicar` faz backup do dia, sobe vídeo e capa em caminho imutável, confere
  o hash público, grava a linha só se o dia estiver livre e confere como `anon`.
  `publicado.json` no episódio impede republicar; fase `incerto` exige
  reconciliação. Publicar dispara o push do dia pelo cron do app.
- Saída: `~/Studio/pulso-videos/diario/AAAA-MM-DD-semanal/`, com MP4, capa,
  pauta e manifesto. Log do Mac na pasta `diario/logs`.

Pré-requisitos do Mac: Pillow, FFmpeg, Codex CLI autenticado com acesso a busca,
fontes Inter, contorno IBGE e clipe ilustrativo em
`~/Studio/pulso-videos/assets/semanal`, mais o ambiente Kokoro do Studio.
A voz oficial é usada quando o acesso já existe no processo; a voz de reserva
é declarada no manifesto. Não é necessário provisionar outras contas.

```sh
python3 tools/pulso-semanal/render.py /caminho/pauta.json \
  --data AAAA-MM-DD --saida /caminho/episodio
```

## Agenda neste Mac

`~/Library/LaunchAgents/com.lion.pulso-news-semanal.plist` agenda domingo às
05:30, com segunda janela às 06:30 no horário do Mac (fuso de Cuiabá na
instalação). O script também checa o domingo pelo fuso `America/Cuiaba`.
Se o usuário não estiver com a sessão do Mac ativa ou não houver rede, não
há execução de nuvem. Uma edição final já existente impede nova pesquisa
ou render. O log local registra falhas e confirma a deduplicação.

Publicar no app depois de assistir o candidato:

```sh
python3 tools/pulso-semanal/app.py publicar ~/Studio/pulso-videos/diario/AAAA-MM-DD-semanal
python3 -m unittest discover -s tools/pulso-semanal -p 'test_*.py'
```

Para testar só a apuração e conferência, sem alterar vídeo ou publicar:

```sh
python3 tools/pulso-semanal/domingo.py --somente-pauta /tmp/pauta-semanal.json
```
