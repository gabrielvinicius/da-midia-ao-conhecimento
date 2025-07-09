// src/components/auth/login-form.tsx
"use client";

import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {saveToken} from "@/lib/auth";

const schema = z.object({
    username: z.string().email(),
    password: z.string().min(6),
});

type FormData = z.infer<typeof schema>;

export function LoginForm() {
    const { register, handleSubmit, formState } = useForm<FormData>({
        resolver: zodResolver(schema),
    });
    const router = useRouter();

    const onSubmit = async (data: FormData) => {
        try {
            const params = new URLSearchParams();
            params.append("username", data.username);
            params.append("password", data.password);
            // grant_type, scope, client_id, client_secret são opcionais no seu backend
            const response = await api.post("/auth/login", params, {
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
            });
            saveToken(response.data.access_token);
            router.push("/dashboard");
        } catch (error) {
            alert("Erro ao fazer login.");
        }
    };

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 w-[300px]">
            <div>
                <Label>Email</Label>
                <Input {...register("username")} type="email" />
            </div>
            <div>
                <Label>Senha</Label>
                <Input {...register("password")} type="password" />
            </div>
            <Button type="submit" disabled={formState.isSubmitting}>
                Entrar
            </Button>
        </form>
    );
}
