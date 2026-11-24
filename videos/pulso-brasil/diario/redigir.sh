#!/usr/bin/env bash
# Lê o stdin e troca por [redigido] o que tem cara de chave (JWT, sk-ant, sk_, sb_secret_, github_pat_, ghp_/ghs_,
# AIza) e o valor de cabeçalho de autenticação. Usado antes de qualquer log ir para artifact ou issue (públicos).
# Padrão por forma: não conhece o valor dos segredos, então log só entra no artifact em trecho curto (tail).
# O delimitador do sed é # (a barra aparece dentro dos colchetes e muda de significado entre GNU e BSD).
exec sed -E \
  -e 's#(eyJ|sk-ant-|sk_|sb_secret_|AIza|github_pat_|ghp_|ghs_)[A-Za-z0-9_.-]{16,}#[redigido]#g' \
  -e 's#([Aa]uthorization|[Aa]pikey|xi-api-key|x-api-key)([:=" ]+)(Bearer +|Basic +)?[A-Za-z0-9_.+/=-]{12,}#\1\2[redigido]#g'
