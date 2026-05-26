import hashlib
import secrets

def generate_api_key() -> str:
    """
    Gera uma chave de API segura em texto cru.
    Exemplo de saída: vettipster_live_8e72ba63f10d48f98a28
    """
    random_part = secrets.token_hex(16)
    return f"vettipster_live_{random_part}"

def hash_api_key(key: str) -> str:
    """
    Retorna o hash SHA-256 correspondente à chave fornecida.
    """
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()
