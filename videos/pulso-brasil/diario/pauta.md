Você prepara o episódio diário do Pulso Brasil (vídeo de ~50 s para o app e o Instagram).
Só escreve arquivos na pasta do dia. Não publica, não renderiza, não chama voz.

Entradas (no fim deste texto): Dia, Pasta e Molde.

1. Dados
   - O agendador já gravou, por script, os dados do dia em `fontes/` (você não busca nem
     transcreve dado; não há banco nem rede para você):
     `fontes/bcb-ptax.json` (PTAX, Banco Central, Olinda, últimos 15 dias),
     `fontes/pulso-imea.json` (IMEA soja e milho de MT na semana do último pregão, e as praças
     da soja nesse dia; chave `imea_mt`, `pracas_soja_<data>`) e `fontes/pulso-imea.sql` (a
     consulta usada). Leia, não altere nenhum dos três nem crie arquivo em `fontes/`: o
     agendador confere depois e descarta o episódio se algum mudou ou se `fontes/` ganhou arquivo.
   - Sem PTAX nem IMEA novos desde o último episódio em `Molde/historico.jsonl`:
     não escreva episódio; grave `sem-episodio.txt` com o motivo em uma linha e pare.

2. Escreva `episodio.json` e `dossie.json` seguindo `Molde/episodio.schema.json`,
   `Molde/exemplos/` e o episódio de 2026-11-24 em `Molde/exemplos/2026-11-24-dolar-soja/`
   (`episodio.json`, `dossie.json`, `fontes/`) como modelo de forma (não de conteúdo).
   - Cada número do roteiro, das cenas, da legenda e de `numeros_chave` sai de uma linha
     do dossiê com `json_campo` apontando para o arquivo em `fontes/`; conta derivada vai em
     `derivados` com a fórmula.
   - O dado mais recente de cada série (PTAX, IMEA MT e as praças citadas) leva `banco`
     (serie, commodity, localidade, indicador, campo, data) como no exemplo; o gate de frescor
     do app confere isso no banco na hora de publicar. Ponto antigo da comparação usa
     `"banco": null` com `isento_motivo`.
   - Tema novo: não repita tema nem número-chave de `Molde/historico.jsonl`.
   - Só fato e aritmética. Nada de causa que os dados não provam ("o câmbio segurou"),
     previsão ("se o dólar continuar...") nem orientação de venda. Diferença entre praças
     "pode incluir frete e logística".
   - Roteiro: número na fala por extenso com marcação `*{exibe|fala}*`; data com
     `{dia 23|dia vinte e três}` para a legenda não partir a data. Escreva "PTAX"
     (a voz já diz "petax").
   - Gráfico `serie_linha`: todos os pontos da série, em ordem de data.
   - Clipe de fundo (`clipe`): só chave de `Molde/assets/manifest.json` com destino `cenas/`.
     Prefira os 17 de origem `fundos-omni/` (campo, chuva, colheita, estrada, grãos, milho,
     porto, silos, soja); um clipe diferente por cena, ligado ao assunto da cena (cultura
     errada, como milho num episódio de soja, não entra) e sem repetir a sequência de
     clipes do episódio anterior.
   - `legenda_instagram` rica: série dia a dia dos números do vídeo, a conta explicada,
     a ressalva "IMEA é indicador, não preço de balcão. Não é recomendação de venda.",
     dias sem dado (feriado) ditos, chamada para o app e até 5 hashtags.
   - Título e push: fato com número, sem causa.

3. Confira antes de sair: `python3 Molde/episodio.py <Pasta>/episodio.json` aprovado.
   Não rode `--travar`; o agendador trava depois de você.
