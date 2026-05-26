# Blaze Double API - Scraper e Distribuidor Real-time

Este microsserviço é responsável por capturar os giros em tempo real do jogo **Double** da Blaze via conexão WebSocket direta e distribuí-los instantaneamente via WebSockets e APIs REST.

---

## 🏗️ Funcionamento Técnico

1. **Scraper Resiliente:** Conecta-se diretamente ao WebSocket da Blaze utilizando um mecanismo de backoff exponencial em caso de quedas de rede.
2. **Distribuição em Tempo Real:** Dispara transmissões via WebSocket para todos os clientes conectados (como o frontend do dashboard) instantaneamente após cada giro.
3. **Persistência local:** Armazena resultados em cache local e faz limpeza periódica automática de registros com mais de 10 dias para economizar recursos.
4. **Integração:** Conecta-se à rede interna `evolution-api_internal-99` para aproveitar as configurações compartilhadas de bancos de dados.

---

## ⚙️ Limites de Recursos Configurados

Para otimizar os recursos do servidor e proteger contra estouros de CPU e RAM:
* **CPU Máxima:** `0.30` (30% de um núcleo de CPU)
* **Memória RAM Máxima:** `250MB`

---

## 🚀 Como Executar

O serviço necessita da chave secreta de rede `s-d-internal` configurada nos secrets para autorizar requisições do dashboard.

Suba o container:
```bash
docker compose up -d
```

---

## 🔌 Endpoints Principais

* **GET `/double/v1/results`:** Obtém os últimos giros salvos no banco.
* **GET `/double/v1/stats`:** Estatísticas de cores agrupadas hora a hora.
* **POST `/double/v1/backtest`:** Simula assertividade de estratégias no histórico.
* **WS `/double/v1/ws/live?api_key=...`:** Rota de WebSocket persistente para escutar giros em tempo real.
