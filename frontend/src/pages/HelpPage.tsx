import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { Card } from "@/components/ui/Card";
import { ACCEPTED_EXTENSIONS, MAX_FILE_SIZE_MB } from "@/features/media/uploadFile";

type Section = { title: string; body: ReactNode };

const formats = ACCEPTED_EXTENSIONS.map((ext) => ext.replace(".", "").toUpperCase()).join(", ");

const SECTIONS: Section[] = [
  {
    title: "O que a plataforma faz com cada arquivo",
    body: (
      <>
        <p>
          Vídeos e áudios são transcritos; nos vídeos, o que aparece na tela também é descrito. Documentos e imagens têm o
          texto extraído (com leitura de imagem nos escaneados).
        </p>
        <p>
          Depois, o texto é analisado: resumo de acordo com o tipo de conteúdo (aula, palestra, reunião...), capítulos,
          perguntas de revisão, temas e tom. Tudo fica indexado para a <Link to="/search">Busca</Link> pelo significado.
        </p>
      </>
    ),
  },
  {
    title: "Arquivos aceitos e limites",
    body: (
      <>
        <p>Formatos: {formats}.</p>
        <p>
          Até {MAX_FILE_SIZE_MB} MB por arquivo. Arquivos grandes são enviados em partes automaticamente: se a conexão cair,
          a parte é repetida, sem recomeçar do zero.
        </p>
      </>
    ),
  },
  {
    title: "Quanto tempo leva",
    body: (
      <>
        <p>
          Uma aula em vídeo de 30 minutos leva cerca de 4 minutos. O servidor processa uma mídia por vez: com outras na
          fila, a sua espera a vez.
        </p>
        <p>
          Não precisa deixar a página aberta. O sino avisa quando cada etapa termina, e os{" "}
          <Link to="/notifications">Avisos</Link> guardam o histórico.
        </p>
      </>
    ),
  },
  {
    title: "O que você encontra na página de cada mídia",
    body: (
      <p>
        O reprodutor com a transcrição sincronizada (clique num trecho para ir ao momento), o resumo, os capítulos, as
        perguntas de revisão, os temas com os trechos de cada um e o que apareceu na tela. Pelo menu de exportação você
        baixa o resumo, a transcrição (texto, SRT ou WebVTT) e o guia de estudo, ou imprime em PDF.
      </p>
    ),
  },
  {
    title: "Corrigir o que a IA errou",
    body: (
      <p>
        O resumo, os títulos dos temas, os capítulos, as perguntas e qualquer trecho da transcrição podem ser editados. A
        versão da IA fica guardada, e a correção da transcrição vale na próxima análise. Avaliar o resultado (com o polegar
        no resumo) ajuda a medir a qualidade da plataforma.
      </p>
    ),
  },
  {
    title: "Como funciona a Revisão",
    body: (
      <p>
        Em <Link to="/study">Revisão</Link> ficam as perguntas de todas as mídias. Responda de cabeça, abra a resposta e
        marque se acertou: o que você acerta volta em 1, 3, 7 e 14 dias; o que erra volta no mesmo dia. A partir da quarta
        caixa, a pergunta conta como dominada.
      </p>
    ),
  },
  {
    title: "Resumos e Temas",
    body: (
      <p>
        <Link to="/notebook">Resumos</Link> junta os resumos de todas as mídias para ler em sequência, baixar ou imprimir.{" "}
        <Link to="/topics">Temas</Link> mostra os assuntos de todas elas; os que aparecem em mais de uma mídia vêm primeiro,
        com o link para cada trecho.
      </p>
    ),
  },
  {
    title: "Quando algo falha",
    body: (
      <p>
        A mídia aparece como “Falhou”, com o motivo em linguagem simples, e o botão “Tentar novamente” a processa de novo.
        Se uma etapa opcional falhar (o tom, por exemplo), as demais ficam disponíveis e o aviso diz qual faltou.
      </p>
    ),
  },
  {
    title: "Privacidade",
    body: (
      <p>
        Os arquivos são processados neste servidor, sem serviços externos de IA. Só você vê as suas mídias; os
        administradores podem vê-las para resolver problemas.
      </p>
    ),
  },
];

/** Como funciona: o que a plataforma faz, limites, tempos e como aproveitar cada tela. */
const HelpPage = () => (
  <div className="mx-auto max-w-3xl space-y-6">
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Como funciona</h1>
      <p className="text-sm text-muted-foreground">O que acontece com os seus arquivos e como aproveitar cada tela.</p>
    </div>
    <Card className="divide-y divide-slate-100 border-[#ede4d5]">
      {SECTIONS.map((section, index) => (
        <details key={section.title} className="group p-4 sm:p-5" open={index === 0}>
          <summary className="cursor-pointer list-none font-medium text-slate-900 marker:hidden">
            <span className="mr-2 inline-block text-muted-foreground transition-transform group-open:rotate-90">›</span>
            {section.title}
          </summary>
          <div className="mt-2 space-y-2 pl-5 text-sm leading-relaxed text-slate-700 [&_a]:font-medium [&_a]:text-slate-900 [&_a]:underline">
            {section.body}
          </div>
        </details>
      ))}
    </Card>
  </div>
);

export default HelpPage;
