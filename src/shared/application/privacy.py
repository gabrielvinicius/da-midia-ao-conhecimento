"""Dados pessoais fora dos logs (RNF06).

Os logs são JSON e são coletados; um e-mail ou o texto de uma busca neles
sairia do banco, onde a exclusão da conta o apaga, para um lugar onde não
apaga.
"""
from __future__ import annotations

import hashlib


def masked_email(email: str | None) -> str:
    """``ana@ifba.edu.br`` vira ``a***@ifba.edu.br#3f2a``: dá para seguir as
    tentativas de uma mesma conta sem guardar o endereço."""
    email = (email or "").strip().lower()
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    digest = hashlib.sha256(email.encode()).hexdigest()[:4]
    return f"{local[:1]}***@{domain}#{digest}"


def masked_ip(ip: str | None) -> str:
    """``203.0.113.42`` vira ``203.0.x.x#17af``: o endereço IP também é dado
    pessoal (LGPD); a marca segue as tentativas da mesma origem sem guardá-lo."""
    ip = (ip or "").strip()
    if not ip:
        return "***"
    digest = hashlib.sha256(ip.encode()).hexdigest()[:4]
    if "." in ip:
        prefix = ".".join(ip.split(".")[:2]) + ".x.x"
    else:
        prefix = ip.split(":")[0] + ":x"
    return f"{prefix}#{digest}"


__all__ = ["masked_email", "masked_ip"]
