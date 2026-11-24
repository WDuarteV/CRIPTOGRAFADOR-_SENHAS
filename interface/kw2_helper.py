#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helpers compartilhados para criptografia/descriptografia em 2 camadas (Dicionário + Palavra-Chave KW2)."""

import hashlib
import hmac


def compute_token_for_char(char_code: int, key: int, size: int):
    """Calcula deterministamente o token da tabela (Passo 1) para um código ASCII."""
    idx = (char_code * key) % size
    valor = idx * key
    for _ in range(50):
        valor = (valor * 31 + 17) % 1000000007
    raw = f"subst_{valor}"
    return raw[::-1], idx, valor


def find_worker_for_index(idx: int, size: int, workers: int):
    """Determina qual worker paralelo [0..P-1] processou o índice idx."""
    if workers <= 1:
        return 0, 0, size
    chunk = size // workers
    w = min(workers - 1, idx // chunk) if chunk > 0 else 0
    start_idx = w * chunk
    end_idx = size if w == workers - 1 else start_idx + chunk
    return int(w), int(start_idx), int(end_idx)


def derive_keyword_key(keyword: str, key: int, size: int) -> bytes:
    """Deriva chave de 256 bits via 10.000 iterações SHA-256 (espelha kw2::derive_keyword_key em C++)."""
    salt = f"SO2_KW2_SALT:{key}:{size}"
    kw_bytes = keyword.encode("utf-8")
    dk = hashlib.sha256(b"KEY:" + kw_bytes + b"|" + salt.encode("utf-8")).digest()
    for r in range(10000):
        dk = hashlib.sha256(dk + r.to_bytes(2, "little") + kw_bytes).digest()
    return dk


def compute_mac_tag(dk: bytes, cipher_bytes: bytes) -> bytes:
    """Calcula tag de integridade SHA-256 (16 bytes)."""
    mac_key = hashlib.sha256(dk + b"MAC").digest()
    return hashlib.sha256(mac_key + cipher_bytes).digest()[:16]


def decrypt_with_keyword(cipher_text: str, keyword: str, key: int, size: int):
    """Remove a camada KW2 validando a palavra-chave secreta e o MAC de integridade."""
    text = cipher_text.strip()
    if not text.startswith("KW2$"):
        if keyword:
            return False, (
                "Este código não foi protegido pela camada KW2 (ou foi gerado apenas pelo dicionário). "
                "Deixe a palavra-chave vazia para decifrar tokens legados."
            )
        return True, text

    if not keyword:
        return False, "Este código está protegido por Palavra-Chave (KW2). Informe a palavra-chave secreta para descriptografar."

    parts = text.split("$")
    if len(parts) != 3 or parts[0] != "KW2":
        return False, "Formato de código cifrado KW2 inválido."

    try:
        cipher_bytes = bytes.fromhex(parts[1])
        tag_bytes = bytes.fromhex(parts[2])
    except ValueError:
        return False, "Código cifrado KW2 corrompido (hexadecimal inválido)."

    if not cipher_bytes or (len(cipher_bytes) % 32) != 0 or len(tag_bytes) != 16:
        return False, "Tamanho do bloco ou da tag de integridade KW2 inválido."

    dk = derive_keyword_key(keyword, key, size)
    expected_tag = compute_mac_tag(dk, cipher_bytes)
    if not hmac.compare_digest(expected_tag, tag_bytes):
        return False, "Palavra-chave secreta incorreta, parâmetros (K/N) incompatíveis ou código adulterado."

    padded = bytearray()
    total_blocks = len(cipher_bytes) // 32
    for b in range(total_blocks):
        ks = hashlib.sha256(dk + b"CTR" + b.to_bytes(4, "big")).digest()
        block = cipher_bytes[b * 32:(b + 1) * 32]
        padded.extend(c ^ k for c, k in zip(block, ks))

    pad_len = padded[-1]
    if pad_len == 0 or pad_len > 32 or pad_len > len(padded):
        return False, "Falha de integridade no padding ao descriptografar."
    if bytes(padded[-pad_len:]) != bytes([pad_len]) * pad_len:
        return False, "Falha de integridade no padding ao descriptografar."

    try:
        payload = bytes(padded[:-pad_len]).decode("utf-8")
    except UnicodeDecodeError:
        return False, "Falha ao decodificar payload UTF-8."

    return True, payload


def decrypt_tokens(cipher_text: str, key: int, size: int, workers: int = 4, keyword: str = ""):
    """Descriptografa a camada KW2 (se presente) e depois reverte os tokens no dicionário dinâmico."""
    if not cipher_text.strip():
        return False, "Nenhum código cifrado informado.", []

    ok, payload_or_err = decrypt_with_keyword(cipher_text, keyword, key, size)
    if not ok:
        return False, payload_or_err, []

    tokens = [t.strip() for t in payload_or_err.strip().split("-") if t.strip()]
    reverse_map = {}
    details_map = {}
    for code in range(256):
        tok, idx, val = compute_token_for_char(code, key, size)
        reverse_map[tok] = chr(code)
        w_id, w_start, w_end = find_worker_for_index(idx, size, workers)
        details_map[tok] = {
            "char": chr(code),
            "ascii": code,
            "index": idx,
            "val": val,
            "worker_id": w_id,
            "worker_range": f"[{w_start:,} .. {w_end:,})".replace(",", "."),
        }

    decrypted_chars = []
    steps = []
    for tok in tokens:
        if tok in reverse_map:
            c = reverse_map[tok]
            info = details_map[tok]
            decrypted_chars.append(c)
            steps.append({
                "token": tok,
                "val": info["val"],
                "char": c,
                "ascii": info["ascii"],
                "index": info["index"],
                "worker_id": info["worker_id"],
                "worker_range": info["worker_range"],
                "status": "Validado (KW2 + Dicionário)",
            })
        else:
            decrypted_chars.append("?")
            steps.append({
                "token": tok,
                "val": None,
                "char": "?",
                "ascii": None,
                "index": None,
                "worker_id": None,
                "worker_range": "N/A",
                "status": "Token Desconhecido",
            })

    return True, "".join(decrypted_chars), steps

