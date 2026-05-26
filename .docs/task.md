# Checklist de Tarefas: API Blaze Double Autônoma (ws_double_api)

- `[x]` **1. Estruturação Base e Arquivos de Build**
  - `[x]` Criar pasta do projeto [ws_double_api](file:///opt/docker-apps/projects/minhas-apis/ws_double_api)
  - `[x]` Criar [requirements.txt](file:///opt/docker-apps/projects/minhas-apis/ws_double_api/requirements.txt) com dependências assíncronas
  - `[x]` Criar [Dockerfile](file:///opt/docker-apps/projects/minhas-apis/ws_double_api/Dockerfile) otimizado multi-stage
  - `[x]` Criar [docker-compose.yml](file:///opt/docker-apps/projects/minhas-apis/ws_double_api/docker-compose.yml) configurando volumes e Docker Secrets

- `[x]` **2. Camada Core e Utilitários de Segurança**
  - `[x]` Criar `app/core/meta.py` com o sistema `get_secret` seguro para leitura de `/run/secrets/`
  - `[x]` Criar `app/core/config.py` com Pydantic Settings para compilação dinâmica do DB
  - `[x]` Criar `app/core/security.py` para geração de chaves seguras e validação de hashes SHA-256
  - `[x]` Criar `app/core/websocket_manager.py` para gerenciar conexões em tempo real

- `[x]` **3. Banco de Dados e Modelagem de Dados**
  - `[x]` Criar `app/db/session.py` com suporte assíncrono para SQLite e PostgreSQL
  - `[x]` Criar `app/db/models.py` com as tabelas `DoubleSpin` e `APIKey`

- `[x]` **4. Captador WebSocket Resiliente (Blaze Scraper)**
  - `[x]` Criar `app/services/blaze_scraper.py` implementando o worker assíncrono com handshake Socket.IO, persistência automática e backoff exponencial

- `[x]` **5. Rotas de API e Segurança de Endpoints**
  - `[x]` Criar `app/api/schemas.py` com validações Pydantic para request/response
  - `[x]` Criar `app/api/dependencies.py` para interceptação e validação de chaves de API (HTTP e WS)
  - `[x]` Criar `app/api/routes.py` com rotas de dados (/results, /stats, /history, /fullday e WebSocket /ws/live)
  - `[x]` Criar `app/api/admin.py` com gerenciamento administrativo de chaves de API protegido por Token Admin de Secret

- `[x]` **6. Arquivo Principal e Verificação do Fluxo**
  - `[x]` Criar [main.py](file:///opt/docker-apps/projects/minhas-apis/ws_double_api/main.py) com lifespans para carregar worker e criar tabelas automaticamente
  - `[x]` Testar o fluxo completo de ponta a ponta e auditoria de funcionamento das credenciais
