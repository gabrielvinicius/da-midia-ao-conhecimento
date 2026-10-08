// Nome do projeto: aparece só na interface e nos documentos; os nomes técnicos
// (pacote, imagens, contêineres) são neutros.
export const APP_NAME = "Da Mídia ao Conhecimento";
export const APP_DESCRIPTOR = "Análise de mídia";

/** Marca acima do cartão nas telas de entrada (login, cadastro, conta). */
export const BrandHeader = () => (
  <div className="mb-6 text-center">
    <p className="text-xl font-semibold tracking-tight text-slate-900">{APP_NAME}</p>
    <p className="mt-1 text-xs font-medium uppercase tracking-[0.18em] text-amber-700">{APP_DESCRIPTOR}</p>
  </div>
);
