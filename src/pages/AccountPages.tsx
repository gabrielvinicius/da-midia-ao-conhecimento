import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, MailCheck, XCircle } from "lucide-react";

import { BrandHeader } from "@/components/Brand";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { apiErrorMessage } from "@/lib/errors";
import { forgotPassword, resendVerification, resetPassword, verifyEmail } from "@/features/authentication/api";

const Shell = ({ title, description, children }: { title: string; description?: string; children: ReactNode }) => (
  <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4 py-12">
    <BrandHeader />
    <Card className="w-full max-w-md border border-[#ede4d5] bg-white">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  </div>
);

const BackToLogin = () => (
  <p className="text-center text-sm">
    <Link to="/login" className="underline">
      Voltar para o login
    </Link>
  </p>
);

/** Depois do cadastro: "confira seu e-mail", com o reenvio do link. */
export const CheckEmailPage = () => {
  const [params] = useSearchParams();
  const email = params.get("email") ?? "";
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);

  const resend = async () => {
    setSending(true);
    try {
      await resendVerification(email);
    } finally {
      setSending(false);
      setSent(true);
    }
  };

  return (
    <Shell title="Confirme seu e-mail">
      <div className="flex flex-col items-center gap-3 text-center">
        <MailCheck className="h-10 w-10 text-amber-600" />
        <p className="text-sm text-slate-700">
          Enviamos um link de confirmação para <strong>{email || "o seu e-mail"}</strong>. Abra-o para ativar a conta; ele vale
          por 24 horas.
        </p>
        <p className="text-xs text-slate-500">Não chegou? Confira a caixa de spam ou peça outro link.</p>
      </div>
      {email && (
        <Button variant="outline" className="w-full" onClick={resend} disabled={sending || sent}>
          {sent ? "Se a conta estiver aguardando, um novo link foi enviado" : sending ? "Enviando..." : "Reenviar o link"}
        </Button>
      )}
      <BackToLogin />
    </Shell>
  );
};

/** Aberta pelo link do e-mail: confirma e leva ao login. */
export const ConfirmEmailPage = () => {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [message, setMessage] = useState("");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // o StrictMode chama o efeito duas vezes
    started.current = true;
    verifyEmail(token)
      .then(() => setState("ok"))
      .catch((error) => {
        setMessage(apiErrorMessage(error, "Este link é inválido ou expirou."));
        setState("error");
      });
  }, [token]);

  return (
    <Shell title="Confirmação de e-mail">
      {state === "loading" && (
        <p className="flex items-center justify-center gap-2 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" /> Confirmando...
        </p>
      )}
      {state === "ok" && (
        <>
          <p className="flex items-center justify-center gap-2 text-sm text-emerald-700">
            <CheckCircle2 className="h-5 w-5" /> E-mail confirmado. Sua conta está ativa.
          </p>
          <Button asChild className="w-full">
            <Link to="/login">Entrar</Link>
          </Button>
        </>
      )}
      {state === "error" && (
        <>
          <p className="flex items-center justify-center gap-2 text-center text-sm text-red-700">
            <XCircle className="h-5 w-5 shrink-0" /> {message}
          </p>
          <p className="text-center text-xs text-slate-500">
            Tente entrar: se a conta ainda não estiver confirmada, a tela de login oferece um novo link.
          </p>
          <BackToLogin />
        </>
      )}
    </Shell>
  );
};

/** Pede o link de nova senha. A resposta é a mesma, exista a conta ou não. */
export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      await forgotPassword(email.trim());
      setDone(true);
    } catch (err) {
      setError(apiErrorMessage(err, "Não foi possível enviar agora. Tente de novo em instantes."));
    } finally {
      setSending(false);
    }
  };

  return (
    <Shell title="Esqueci minha senha" description="Enviamos um link para você criar uma nova senha.">
      {done ? (
        <p className="text-center text-sm text-slate-700">
          Se houver uma conta com <strong>{email}</strong>, o link chega em instantes. Ele vale por 1 hora e uma única vez.
        </p>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">E-mail da conta</Label>
            <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} disabled={sending} />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={sending || !email.trim()}>
            {sending ? "Enviando..." : "Enviar o link"}
          </Button>
        </form>
      )}
      <BackToLogin />
    </Shell>
  );
};

const PASSWORD_RULE = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;

/** Aberta pelo link do e-mail: define a nova senha. */
export const ResetPasswordPage = () => {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const problem = !password
    ? null
    : !PASSWORD_RULE.test(password)
      ? "Use pelo menos 8 caracteres, com letras maiúsculas, minúsculas e números."
      : confirm && confirm !== password
        ? "As senhas não são iguais."
        : null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (problem || password !== confirm) return;
    setSaving(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(apiErrorMessage(err, "Este link é inválido, expirou ou já foi usado. Peça um novo."));
    } finally {
      setSaving(false);
    }
  };

  if (done) {
    return (
      <Shell title="Senha alterada">
        <p className="flex items-center justify-center gap-2 text-sm text-emerald-700">
          <CheckCircle2 className="h-5 w-5" /> Pronto. Entre com a nova senha.
        </p>
        <Button asChild className="w-full">
          <Link to="/login">Entrar</Link>
        </Button>
      </Shell>
    );
  }

  return (
    <Shell title="Nova senha">
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="new-password">Nova senha</Label>
          <Input id="new-password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={saving} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="confirm-password">Repita a nova senha</Label>
          <Input id="confirm-password" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} disabled={saving} />
        </div>
        {(problem || error) && <p className="text-sm text-destructive">{problem || error}</p>}
        <Button type="submit" className="w-full" disabled={saving || !password || password !== confirm || Boolean(problem)}>
          {saving ? "Salvando..." : "Salvar a nova senha"}
        </Button>
      </form>
      {error && (
        <p className="text-center text-sm">
          <Link to="/esqueci-a-senha" className="underline">
            Pedir um novo link
          </Link>
        </p>
      )}
    </Shell>
  );
};
