## O que muda e por quê

<!-- O problema, a decisão e o efeito para quem usa ou opera a plataforma. -->

## Validação

<!-- O que foi rodado além da CI (testes locais, implantação de teste, medições). -->

## Riscos e volta atrás

<!-- Migrações de banco, variáveis novas no .env, mudança em volumes ou na
implantação; como desfazer se der errado. -->

## Checklist

- [ ] CI verde (backend, frontend, migrations, deployment; images, se tocou em Dockerfile ou dependências)
- [ ] Variáveis novas documentadas no `.env.example`
- [ ] Documentação em `docs/` atualizada no mesmo PR (guia, explicação ou ADR), e a referência regerada (`python scripts/docs/gerar_referencia.py`) se rotas, configurações ou eventos mudaram
- [ ] `AGENTS.md` atualizado quando uma regra do código mudou
- [ ] Arquitetura preservada (injeção de dependência, camadas, `lint-imports`)
