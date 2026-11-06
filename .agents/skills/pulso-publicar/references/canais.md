# Publicação e recuperação

## Instagram pelo Chrome habitual

Use a janela/perfil já autenticado do dono; confirme visualmente `@pulsodocampo`.
Não ocupe sessão de automação alheia, não abra perfil alternativo por conveniência
e não leia credenciais. Se faltar login, só a autenticação exige a mão do dono.
Use a ferramenta de navegador disponível ou AppleScript quando autorizado pelo
ambiente; identifique controles pela interface observada, sem coordenadas fixas.

Antes do upload, confira se o episódio já aparece no perfil. Se uma tentativa
ficou incerta, reconcilie primeiro; ausência de recibo não prova falha de envio.
Registre em `out/publicacao/estado.json` o `video_sha256` e
`instagram.phase: sharing` **antes** de compartilhar. Não mantenha dois compositores.

Cole `out/legenda.txt` uma única vez em compositor vazio; leia o texto de volta
e use `caption_check(actual, expected)` sem normalizar quebras ou acentos. Ambos
os resultados devem ser verdadeiros. Texto duplicado: descarte o rascunho ruim
antes de criar outro, sem publicar. Confira capa, proporção, duração e rótulo de IA.

Depois de compartilhar, confirme mensagem de sucesso e permalink no perfil correto.
Confira legenda única e rótulo de IA no post. Grave `out/publicado.json` com
`reel`, `conta`, `video_sha256`, `em`, `verificado_em` e observações. Não registre
sucesso por clique, timeout ou conclusão do upload. Story é um canal separado;
não o declare publicado se só o Reel foi enviado.

## Catálogo do app

Leia as instruções Supabase do app antes de operar. Confirme projeto Pulso do Campo
e as colunas reais de `public.pulso_news_episodios`, sem usar nomes por suposição.
Consulte o ID em `out/meta-app.json` e salve backup antes de qualquer escrita.
Existindo linha, compare candidato, caminhos e status; conflito não é sucesso e
não autoriza sobrescrever. Faça reconciliação em vez de INSERT repetido.

Use caminhos novos e imutáveis para vídeo/capa. Confira HTTP 200, tamanho e hash
dos objetos públicos. `insert_sql(meta, video_path, cover_path)` prepara somente
um INSERT com `ON CONFLICT(id) DO NOTHING`; não executa, não muda schema/RLS,
não faz upload e não envia push. Se `RETURNING` vier vazio, releia e compare a
linha existente; nunca conclua publicação só pelo SQL não retornar erro.

Antes da escrita, registre `app.phase: submitted` no journal vinculado ao vídeo.
Após a escrita, confira leitura pública como `anon`, status, conteúdo e mídia.
Grave recibo da operação e verificação; acrescente a `out/publicado.json`:
`app.id`, `app.status: publicado`, `app.aprovado_em`, `app.verificacao`.
Preserve a parte Instagram e finalize o arquivo de forma atômica (temporário + rename).

Sem retorno inequívoco: `phase: uncertain`; próximo passo é reconciliação, não retry.
Catálogo publicado não prova push recebido nem reprodução no iPhone.
