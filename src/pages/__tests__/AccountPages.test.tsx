import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { CheckEmailPage, ConfirmEmailPage, ForgotPasswordPage, ResetPasswordPage } from "@/pages/AccountPages";

const api = {
  verifyEmail: vi.fn(),
  resendVerification: vi.fn(),
  forgotPassword: vi.fn(),
  resetPassword: vi.fn(),
};
vi.mock("@/features/authentication/api", () => ({
  verifyEmail: (...a: unknown[]) => api.verifyEmail(...a),
  resendVerification: (...a: unknown[]) => api.resendVerification(...a),
  forgotPassword: (...a: unknown[]) => api.forgotPassword(...a),
  resetPassword: (...a: unknown[]) => api.resetPassword(...a),
}));

const at = (path: string, element: JSX.Element) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="*" element={element} />
      </Routes>
    </MemoryRouter>,
  );

const apiError = (status: number, detail: string) => ({ isAxiosError: true, response: { status, data: { detail } } });

describe("páginas da conta", () => {
  beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()));

  it("confirma o e-mail pelo link e leva ao login", async () => {
    api.verifyEmail.mockResolvedValue(undefined);
    at("/confirmar-email?token=abc", <ConfirmEmailPage />);
    await waitFor(() => expect(screen.getByText(/E-mail confirmado/)).toBeInTheDocument());
    expect(api.verifyEmail).toHaveBeenCalledTimes(1);
    expect(api.verifyEmail).toHaveBeenCalledWith("abc");
    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/login");
  });

  it("explica um link de confirmação inválido", async () => {
    api.verifyEmail.mockRejectedValue(apiError(400, "Este link é inválido, expirou ou já foi usado. Peça um novo."));
    at("/confirmar-email?token=velho", <ConfirmEmailPage />);
    await waitFor(() => expect(screen.getByText(/já foi usado/)).toBeInTheDocument());
  });

  it("depois do cadastro, reenvia o link para o e-mail informado", async () => {
    api.resendVerification.mockResolvedValue(undefined);
    at("/confirme-seu-email?email=ana%40exemplo.com", <CheckEmailPage />);
    expect(screen.getByText("ana@exemplo.com")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reenviar o link" }));
    await waitFor(() => expect(api.resendVerification).toHaveBeenCalledWith("ana@exemplo.com"));
  });

  it("pede o link de nova senha sem dizer se a conta existe", async () => {
    api.forgotPassword.mockResolvedValue(undefined);
    at("/esqueci-a-senha", <ForgotPasswordPage />);
    fireEvent.change(screen.getByLabelText("E-mail da conta"), { target: { value: " ana@exemplo.com " } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar o link" }));
    await waitFor(() => expect(screen.getByText(/Se houver uma conta com/)).toBeInTheDocument());
    expect(api.forgotPassword).toHaveBeenCalledWith("ana@exemplo.com");
  });

  it("define a nova senha com as regras do cadastro", async () => {
    api.resetPassword.mockResolvedValue(undefined);
    at("/redefinir-senha?token=tok", <ResetPasswordPage />);
    const save = screen.getByRole("button", { name: "Salvar a nova senha" });

    fireEvent.change(screen.getByLabelText("Nova senha"), { target: { value: "fraca" } });
    expect(screen.getByText(/maiúsculas, minúsculas e números/)).toBeInTheDocument();
    expect(save).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Nova senha"), { target: { value: "Nova-senha-1" } });
    fireEvent.change(screen.getByLabelText("Repita a nova senha"), { target: { value: "Nova-senha-1" } });
    fireEvent.click(save);
    await waitFor(() => expect(screen.getByText(/Entre com a nova senha/)).toBeInTheDocument());
    expect(api.resetPassword).toHaveBeenCalledWith("tok", "Nova-senha-1");
  });
});
