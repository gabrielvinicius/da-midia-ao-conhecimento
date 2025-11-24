# Stage6 Pull Request Template

## Checklist
- [ ] `python3 -m pytest -q`
- [ ] `ruff check`
- [ ] `mypy`
- [ ] `docker-compose up --build backend` (quando aplicável)
- [ ] Documentação atualizada (`docs/architecture.md`, ADRs, diagramas)
- [ ] Plano de rollback descrito
- [ ] Logs relevantes anexados (`uvicorn`, workers Celery, etc.)
- [ ] Revisores de domínio confirmados
- [ ] Issues relacionadas linkadas (Stage6-*)

## Resumo
Descreva brevemente o objetivo desta mudança e como ela se encaixa na fase Stage6 correspondente.

## Validações
- **Cenários principais testados:** (liste fluxos ou endpoints exercitados)
- **Smoke tests / integrações:** (compose, celery inspect, etc.)

## Observações
- Riscos conhecidos:
- Plano de monitoramento pós-deploy:

## Checklist adicional (se aplicável)
- [ ] Alterações em dados/migrações documentadas
- [ ] Ajustes de configuração comunicado ao DevOps
- [ ] Frontend impactado revisado com o time de UI
