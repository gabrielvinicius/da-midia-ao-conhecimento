import { ToastContainer } from "react-toastify";

/**
 * Onde aparecem os avisos de toast.success/error/info do app inteiro (erros
 * das ações, confirmação de correções, avisos em tempo real do WebSocket).
 * Sem este contêiner, o react-toastify não mostra nada: ele saiu na
 * reescrita do frontend, em setembro de 2025, e as chamadas ficaram mudas.
 */
export const Toasts = () => (
  <ToastContainer
    position="bottom-right"
    autoClose={5000}
    limit={3}
    newestOnTop
    closeOnClick
    pauseOnFocusLoss={false}
    theme="light"
  />
);

export default Toasts;
