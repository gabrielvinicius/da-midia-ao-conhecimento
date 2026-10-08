# Da Mídia ao Conhecimento (frontend)

Projeto frontend moderno para a aplicação de sumarização de vídeos.

---

## 🔧 Tecnologias Utilizadas

- React 18
- TypeScript
- Tailwind CSS
- Vite
- React Router DOM v6
- Axios
- React Toastify

---

## 🚀 Como Iniciar o Projeto

### 1. Instale as dependências:
```bash
npm install
```

### 2. Rode em desenvolvimento:
```bash
npm run dev
```

---

## 🗂️ Organização

- `src/features/<funcionalidade>/api`: as chamadas HTTP daquela funcionalidade
  (mídias, transcrição, análise, autenticação, avisos, administração). Só
  elas usam o cliente `src/lib/api.ts`.
- `src/features/<funcionalidade>/hooks`: consultas e mutações do TanStack Query.
- `src/services/auth.service.ts`: a sessão (token de acesso na aba, renovação
  única pelo cookie, saída). O cliente HTTP a recebe por `bindSession`, sem
  depender do serviço.
- `src/contexts`: usuário logado (`AuthContext`) e avisos em tempo real
  (`WebSocketContext`).

Erros: o cliente só mostra aviso global para falta de rede, erro do servidor
(5xx), arquivo grande demais (413) e sessão expirada; os demais (404, 409,
422...) são tratados por quem chamou, com `apiErrorMessage`.

---

## ✅ Verificações (as mesmas da CI)

```bash
npm run typecheck   # TypeScript
npm run lint        # ESLint, sem avisos
npm run test:ci     # Vitest: componentes, sessão e contextos
npm run test:e2e    # Playwright: fumaça no build, com a API simulada
```

Para usar um Chromium já instalado no Playwright, defina `PW_CHROMIUM_PATH`.
