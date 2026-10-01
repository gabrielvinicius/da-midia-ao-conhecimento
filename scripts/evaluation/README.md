# Avaliação do TCC

Passo a passo para medir a plataforma na GPU de referência (RTX 3060 12 GB).
Execute os comandos na raiz do repositório, com `DATABASE_URL` apontando
para o banco usado nas medições.

1. Suba o sistema e comece o registro de memória da GPU:

   ```bash
   nvidia-smi --query-gpu=timestamp,memory.used --format=csv -l 1 > vram.csv
   ```

2. Envie as mídias do conjunto de avaliação uma de cada vez, esperando o
   aviso de "Análise concluída" antes da próxima, para que os tempos não se
   misturem. Anote o id de cada mídia (está na URL da página da mídia).

3. Interrompa o `nvidia-smi` (Ctrl+C) e exporte os tempos já no formato de
   tabela LaTeX:

   ```bash
   PYTHONPATH=. python scripts/evaluation/export_timings.py --vram vram.csv
   ```

4. Para a qualidade da transcrição, digite à mão a transcrição de um trecho
   (ou de toda a gravação) em `referencia.txt` e calcule o WER:

   ```bash
   PYTHONPATH=. python scripts/evaluation/wer.py referencia.txt --media-id <id>
   ```

   Se a referência cobrir só um trecho, salve o trecho correspondente da
   transcrição gerada em um arquivo e passe o arquivo no lugar de `--media-id`.

5. A qualidade dos resumos é avaliada por um questionário fora do sistema
   (escala Likert de 1 a 5 para fidelidade, cobertura e clareza), respondido
   por quem assistiu à gravação. O botão 👍/👎 da página da mídia (valores 1 e
   -1 na tabela `analysis_feedback`) serve como indicador complementar.

6. Cada resumo também passa por uma verificação automática de fidelidade:
   frases sem nenhum trecho parecido na transcrição são apontadas na página da
   mídia. Para a tabela do TCC (uma linha por mídia):

   ```bash
   PYTHONPATH=. python scripts/evaluation/export_timings.py --grounding
   ```

   Compare com a nota de fidelidade do questionário: a verificação aponta
   assuntos que não estão na gravação, mas não um número ou nome trocado.
   O limiar (0,80) pode ser calibrado olhando as frases apontadas.
