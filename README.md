# Da Mídia ao Conhecimento

Plataforma que transforma aulas gravadas, áudios e documentos em material de
estudo: transcreve, descreve o que aparece na tela, resume conforme o tipo de
conteúdo (aula, palestra, reunião...), divide a gravação em capítulos, propõe
perguntas de revisão, identifica temas e tom, e permite buscar trechos pelo
significado em todo o acervo. Roda inteira numa única máquina, sem enviar
dados para fora.

**[Documentação completa](docs/README.md)**: tutorial, guias, referência e
explicações.

## Começar

```bash
git clone https://github.com/gabrielvinicius/da-midia-ao-conhecimento.git
cd da-midia-ao-conhecimento
cp .env.example .env        # defina SECRET_KEY, DB_PASSWORD e o administrador
docker compose up -d --build                                              # GPU NVIDIA
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build  # sem GPU
```

Depois, abra <http://localhost:3000>. O passo a passo, com o que esperar de
cada etapa, está em [Primeiros passos](docs/tutoriais/primeiros-passos.md).

## Como é feito

| | |
|---|---|
| **Arquitetura** | Monólito modular em DDD hexagonal: módulos com fronteiras verificadas, conversando por eventos e filas ([explicação](docs/explicacao/arquitetura.md)) |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 17 com pgvector, Celery e Redis |
| **Modelos** | faster-whisper `large-v3-turbo`; Qwen3.5 9B (Gemma 4 de reserva) via Ollama; multilingual-e5-small e bge-reranker-v2-m3; XLM-RoBERTa; BERTopic ([referência](docs/referencia/modelos.md)) |
| **Interface** | React 19, TypeScript 6, TanStack Query e Table, Tailwind 4, Vite 8 |
| **Implantação** | Docker Compose (GPU NVIDIA, AMD ou CPU), implantação contínua com volta automática, cópias com restic ([guia](docs/guias/implantar-em-producao.md)) |
| **Qualidade** | Testes de unidade, integração, ponta a ponta e de interface; verificações de arquitetura, de infraestrutura e da cadeia de suprimentos na CI |

## Documentação

| Para | Página |
|---|---|
| Aprender a usar | [Primeiros passos](docs/tutoriais/primeiros-passos.md) |
| Colocar em produção | [Implantar](docs/guias/implantar-em-producao.md), [publicar na internet](docs/guias/publicar-na-internet.md), [cópias de segurança](docs/guias/copias-de-seguranca.md) |
| Operar no dia a dia | [Comandos](docs/referencia/comandos.md), [solucionar problemas](docs/guias/solucionar-problemas.md) |
| Contribuir | [Desenvolver](docs/guias/desenvolver.md), [regras do código](AGENTS.md) |
| Consultar | [API](docs/referencia/api.md), [configuração](docs/referencia/configuracao.md), [eventos e filas](docs/referencia/eventos-e-filas.md) |
| Entender as decisões | [Arquitetura](docs/explicacao/arquitetura.md), [ADRs](docs/adr/decisions.md) |

O relatório do TCC fica num repositório à parte (`relatorio_tcc`).
