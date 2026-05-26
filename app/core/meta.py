import os

def get_secret(name, default=None):
    """
    Busca um segredo no sistema de secrets do Docker.
    """
    # Mapeamento de nomes amigáveis para nomes de arquivos de segredos do Docker
    mapping = {
        "POSTGRES_PASSWORD": "s-p-22",
        "SECRET_KEY": "s-k-99",
        "ADMIN_TOKEN": "s-d-admin",
        "INTERNAL_KEY": "s-d-internal"
    }
    
    secret_id = mapping.get(name, name.lower())
    
    # 1. Tenta pegar do ambiente (Fallback)
    val = os.getenv(name)
    if val:
        return val
    
    # 2. Tenta pegar do sistema de secrets do Docker
    for path in [
        f"/run/secrets/{secret_id}",
        f"/run/secrets/{secret_id}.txt"
    ]:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return f.read().strip()
            except Exception:
                continue
                
    return default
