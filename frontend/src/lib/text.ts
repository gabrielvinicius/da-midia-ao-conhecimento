/** Minúsculas e sem acentos, para buscas que acham "Proteção" ao digitar "protecao". */
export const normalizeText = (text: string) => text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
