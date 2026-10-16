# Atualizar dependências

O Dependabot propõe atualizações toda segunda-feira, e cada proposta passa
pela CI. Este guia diz o que fazer com elas.

## O que o Dependabot propõe

| Ecossistema | Como chega |
|---|---|
| Python (`requirements.txt`) | Versões menores e correções num PR agrupado; versões maiores, uma por PR |
| Frontend (`frontend/package.json`) | Idem |
| Ações dos workflows | Agrupadas; atualizam o commit fixado e o comentário com a versão |
| Imagens (Dockerfiles e Compose) | Uma por PR |

Algumas versões maiores ficam de fora de propósito (`.github/dependabot.yml`),
cada uma com o motivo ao lado:

- **`torch` e `torchvision`**: fixados juntos e ligados ao CUDA da imagem
  (ADR-014); sobem à mão, com a medição de tempo e memória na GPU.
- **`transformers` 4.50 ou mais** e **`sentence-transformers` 6**: o Moondream 2
  usa uma revisão de 2024 que exige o `transformers` abaixo de 4.50.
- **`av` (PyAV) 19**: o `faster-whisper` 1.2.1 passa ao `av.open` um
  argumento que o PyAV 19 removeu, e toda transcrição falha. O teste
  `tests/integration/media_processing/test_audio_decoding.py` pega o caso.
- **TypeScript 7**: o typescript-eslint ainda não o aceita.
- **`@types/node`** e **Node**: seguem a versão LTS da imagem e da CI.

## Versões menores e correções

Com a CI verde, faça o merge. Uma falha num PR desses costuma vir do próprio
pacote; leia o log antes de reexecutar. **Não faça o merge com a CI
vermelha**: a implantação só roda depois da CI verde na `main`, e um PR
quebrado ali segura todas as implantações seguintes.

## Versões maiores

Uma versão maior pode exigir mudança no código mesmo com a CI verde, ou quebrar
a CI de um jeito que só aparece depois do merge. Por isso:

1. **Leia o guia de migração** do pacote antes do merge. Pacotes atuais
   costumam trazer um (o react-table 9 traz o seu em
   `node_modules/@tanstack/react-table/skills`).
2. **Uma versão maior por PR**, com a migração do código junto, para que uma
   regressão aponte para uma única causa.
3. **No frontend, compare as telas.** A atualização de 2026 (Tailwind 4,
   Vite 8, ESLint 10, react-table 9 e React 19, PRs #132 a #136) foi validada
   com capturas de 31 telas antes e depois de cada passo, com a API simulada.
   Elas encontraram o que os testes não pegavam: rótulos colados nos campos,
   foco fora do diálogo e uma fila de envio que reenviava o mesmo arquivo.
4. **Meça o que pode piorar.** Peso do JavaScript por tela, tempo e memória na
   GPU: escreva os números antes e depois na descrição do PR.

Quando uma versão maior não puder subir agora, feche o PR com o motivo e
acrescente a regra em `.github/dependabot.yml`, com o comentário.

## Veja também

- [Desenvolver](desenvolver.md): as verificações que a CI roda.
- ADR-016: a cadeia de suprimentos da CI (ações fixadas pelo commit, imagens
  varridas pelo Trivy).
