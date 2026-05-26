# TesteDeep5 — CISO Intelligence Dashboard
### Automated Threat Clustering, Kill Chain Correlation & AI-Powered Intelligence Reporting

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vite](https://img.shields.io/badge/Vite-5.0+-646CFF.svg)](https://vitejs.dev/)
[![ENISA NIS2](https://img.shields.io/badge/framework-ENISA%20NIS2-green.svg)](https://www.enisa.europa.eu/)
[![MITRE ATT&CK](https://img.shields.io/badge/framework-MITRE%20ATT%26CK-red.svg)](https://attack.mitre.org/)

---

## Índice

1. [Resumo Académico](#1-resumo-académico)
2. [Motivação e Contexto](#2-motivação-e-contexto)
3. [Arquitectura do Sistema](#3-arquitectura-do-sistema)
4. [Módulos do Projecto](#4-módulos-do-projecto)
   - 4.1 [Agent 1 — Motor de Clustering](#41-agent-1--motor-de-clustering)
   - 4.2 [Agent 2 — Motor de Reporting](#42-agent-2--motor-de-reporting)
   - 4.3 [SOC Dashboard — Backend](#43-soc-dashboard--backend)
   - 4.4 [SOC Dashboard — Frontend](#44-soc-dashboard--frontend)
   - 4.5 [SOC Dashboard — SSE Server](#45-soc-dashboard--sse-server)
   - 4.6 [Redshift Chrome Extension](#46-redshift-chrome-extension)
   - 4.7 [Módulos Raiz](#47-módulos-raiz)
5. [Modelo de Dados — Estrutura do Alerta](#5-modelo-de-dados--estrutura-do-alerta)
6. [Kill Chain & Phase Map](#6-kill-chain--phase-map)
7. [Mapeamento Phase → Categoria CISO](#7-mapeamento-phase--categoria-ciso)
8. [Modelo de Scoring e Estados CISO](#8-modelo-de-scoring-e-estados-ciso)
9. [Catálogo de Categorias CISO (16)](#9-catálogo-de-categorias-ciso-16)
10. [Lógica de Clustering do Agente 1](#10-lógica-de-clustering-do-agente-1)
11. [Descarte de Ruído Operacional](#11-descarte-de-ruído-operacional)
12. [Mapeamento Secundário via primary_ciso](#12-mapeamento-secundário-via-primary_ciso)
13. [Sistema de Logging](#13-sistema-de-logging)
14. [Instalação](#14-instalação)
15. [Dependências](#15-dependências)
16. [Configuração](#16-configuração)
17. [Utilização](#17-utilização)
18. [Dataset de Testes](#18-dataset-de-testes)
19. [Resultados Esperados por Janela Temporal](#19-resultados-esperados-por-janela-temporal)
20. [Alinhamento Regulatório](#20-alinhamento-regulatório)
21. [Limitações Conhecidas](#21-limitações-conhecidas)
22. [Referências](#22-referências)

---

## 1. Resumo Académico

O **TesteDeep5** é um sistema integrado de correlação e triagem automática de alertas de cibersegurança, desenhado para apoiar Centros de Operações de Segurança (SOC) e Directores de Segurança da Informação (CISO) na detecção precoce, classificação e reporte de ataques multi-fase, no âmbito do projeto **"Agente IA de Interpretação 360º de Incidentes de Cibersegurança e CVEs Associados"**

O sistema implementa uma pipeline end-to-end composta por:

- **Agent 1** — Motor de clustering temporal com grafo de hipóteses probabilístico. Agrupa alertas por categoria CISO dominante via janela deslizante, aplica pesos de fase de kill chain e calcula scores de risco acumulados.
- **Agent 2** — Motor de análise e reporting com LLM integrado. Consome os clusters do Agent 1 e produz intelligence cards estruturados, relatórios LaTeX e visualizações de grafo.
- **SOC Dashboard** — Interface web full-stack (FastAPI + TypeScript/Vite) com visualização em tempo real via Server-Sent Events (SSE), timeline de alertas, painel de janelas e integração CVE.
- **Redshift Chrome Extension** — Extensão de browser para integração com o dashboard SOC directamente no contexto de trabalho do analista.
- **IOC Extractor** — Módulo de extracção automática de Indicators of Compromise dos alertas processados.

O modelo de ameaça é alinhado com MITRE ATT&CK, ENISA NIS2, GDPR Art.33, DORA Art.17 e a Cyber Kill Chain de Lockheed Martin. O sistema é determinístico e auditável ao nível do motor de clustering — todas as decisões de classificação são rastreáveis a regras explícitas.

---

## 2. Motivação e Contexto

Os SOC modernos enfrentam um volume crescente de alertas que excede a capacidade humana de triagem manual. Estudos recentes indicam que analistas SOC recebem em média 1.000 a 10.000 alertas por dia, dos quais 50% a 70% são falsos positivos ou ruído operacional.

O problema central não é a detecção isolada de ameaças — os SIEM e EDR modernos fazem-no razoavelmente bem — mas sim a **correlação temporal e contextual** de alertas dispersos que, individualmente, parecem baixa severidade mas que, em conjunto, revelam um ataque multi-fase em curso.

O TesteDeep5 aborda este problema através de cinco mecanismos complementares:

1. **Clustering por categoria CISO dominante** — agrupa alertas semanticamente relacionados dentro de uma janela deslizante, reduzindo o ruído e aumentando o sinal.
2. **Grafo de hipóteses probabilístico** — modela relações de causalidade entre alertas, calculando probabilidades de progressão para fases mais avançadas.
3. **Classificador probabilístico** — pondera cada alerta de acordo com a sua posição na progressão do ataque e contexto histórico da janela.
4. **LLM integrado para narrative intelligence** — o Agent 2 usa um modelo de linguagem para produzir análise contextual, correlação de TTPs e recomendações de resposta.
5. **Mapeamento regulatório automático** — identifica em tempo real obrigações de notificação NIS2/GDPR/DORA desencadeadas pelos eventos detectados.

---

## 3. Arquitectura do Sistema

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      FONTES DE ALERTAS (Input)                           │
│     SIEM · EDR · IDS · WAF · DLP · DNS · EmailGateway · GRC-Tool         │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │  stream de alertas (formato estruturado)
                               ▼
                        ┌───────────────┐
                        │  launcher.py  │  ← ponto de entrada principal
                        │  shared_config│  ← configuração global
                        └──────┬────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
┌─────────────────────────┐       ┌─────────────────────────────────────┐
│        AGENT 1          │       │             AGENT 2                 │
│  Motor de Clustering    │─────▶│    Motor de Análise & Reporting     │
│                         │       │                                     │
│  • window_manager.py    │       │  • supervisor.py                    │
│  • hypothesis_graph.py  │       │  • llm_engine.py                    │
│  • probabilistic_       │       │  • llm_quality.py                   │
│    classifier.py        │       │  • analyzers.py                     │
│  • mappings.py          │       │  • graph_reporter.py                │
│  • main.py              │       │  • latex_generator.py               │
└─────────────────────────┘       └───────────────┬─────────────────────┘
                                                  │
              ┌───────────────────────────────────┤
              │                                   │
              ▼                                   ▼
┌─────────────────────────┐       ┌──────────────────────────────────────┐
│     IOC EXTRACTOR       │       │          SOC DASHBOARD               │
│  ioc_extractor.py       │       │                                      │
└─────────────────────────┘       │  Backend (FastAPI)                   │
                                  │  • api/siem.py                       │
              ┌───────────────────│  • api/analysis.py                   │
              │                   │  • api/cve.py                        │
              ▼                   │  • services/llm_service.py           │
┌─────────────────────────┐       │  • sse_server.py (real-time)         │
│  REDSHIFT EXTENSION     │       │                                      │
│  Chrome Extension       │       │  Frontend (TypeScript/Vite)          │
│  • background.ts        │       │  • alert_timeline                    │
│  • content.ts           │       │  • windows_panel                     │
│  • popup.ts/html/css    │       │  • graph_viz                         │
└─────────────────────────┘       │  • agent2 card renderer              │
                                  └──────────────────────────────────────┘
```

### Fluxo de dados end-to-end

```
Alertas SIEM
    │
    ▼
launcher.py ──► Agent 1 (clustering + scoring)
                    │
                    ├──► reports/agent1/  (clusters JSON)
                    │
                    ▼
              Agent 2 (LLM analysis + reporting)
                    │
                    ├──► reports/agent2/  (intelligence cards + LaTeX)
                    │
                    ▼
              SOC Dashboard Backend (FastAPI)
                    │
                    ├──► SSE stream ──► Frontend (real-time)
                    │
                    └──► REST API ──► Redshift Extension
```

---

## 4. Módulos do Projecto

### 4.1 Agent 1 — Motor de Clustering

Localização: `agent1/`

| Ficheiro | Responsabilidade |
|---|---|
| `main.py` | Ponto de entrada do agente. Orquestra o pipeline de clustering: leitura de alertas → filtragem → mapeamento → clustering → scoring → output. |
| `window_manager.py` | Gestão da janela deslizante (*sliding window*). Mantém o estado temporal dos alertas activos, calcula intervalos entre eventos e dispara clustering quando os limiares são atingidos. |
| `hypothesis_graph.py` | Grafo de hipóteses — modela relações causais entre alertas como um grafo dirigido acíclico (DAG). Cada nó representa um alerta; as arestas representam relações de progressão kill chain. Calcula probabilidades de avanço para fases mais severas. |
| `probabilistic_classifier.py` | Classificador probabilístico que pondera alertas com base na fase kill chain, contexto histórico da janela e probabilidades do grafo de hipóteses. Produz scores de confiança por categoria CISO. |
| `mappings.py` | Definição do Phase Map completo: `(Category, Type) → (Fase, Peso)`. Inclui mapeamento `Phase → CISO Category` e tabelas de keyword matching para o mapeamento secundário via `primary_ciso`. |

### 4.2 Agent 2 — Motor de Reporting

Localização: `agent2/`

| Ficheiro | Responsabilidade |
|---|---|
| `supervisor.py` | Supervisor do Agent 2. Garante processamento contínuo da fila de relatórios: polling ao `HypothesisGraph` a cada N segundos, processamento da fila persistente com retry exponencial e recuperação automática após falhas. Não despacha diretamente para analisadores — orquestra o `GraphReporter` e o `ReportGenerator`. |
| `llm_engine.py` | Motor LLM do Agent 2. Suporta múltiplos providers (`ollama`, `anthropic`, `openai`/LiteLLM) configuráveis via `shared_config`. Inclui `LLMEnhancer` (análise narrativa), `IncidentAnalyzer` (análise determinística), `CVERepository`, `MITREMapper` e `CVEReportGenerator`. Seleciona provider em runtime via `LLM_PROVIDER2`. |
| `llm_quality.py` | Monitorização de qualidade das respostas LLM. Implementa: `LLMCache` (cache por hash com TTL), `LLMQualityMetrics` (validação de respostas, detecção de breach language não confirmada, IPs privados em recomendações de bloqueio), `ComplexityCalculator` (seleção dinâmica de modelo por complexidade do incidente) e `ChainOfThoughtGenerator` (prompts CoT para rastreabilidade). |
| `analyzers.py` | Extração e formatação de dados para relatórios. `DataExtractor`: extrai IOCs (IPs externos, URLs, CVEs) e assets dos alertas, com fallback inline se `ioc_extractor.py` não estiver disponível. `TimelineBuilder`: constrói timeline de alertas. `DashboardReportFormatter`: formata output para o dashboard. |
| `graph_reporter.py` | Motor central de geração de relatórios do Agent 2. Monitoriza o `HypothesisGraph` (Agent 1), deteta hipóteses confirmadas e gera intelligence cards JSON completos com: análise LLM (se disponível), relatórios LaTeX (CISO e SOC), timeline, IOCs, assets, TTPs, recomendações e flags regulatórias. Emite os cards via SSE para o dashboard. |
| `latex_generator.py` | Gerador de relatórios LaTeX. Produz dois tipos: `CISOReportGenerator` (relatório executivo para o CISO — contexto táctico, impacto, regulamentação) e `SOCReportGenerator` (relatório técnico para o SOC — timeline, severity breakdown, resposta faseada). |

### 4.3 SOC Dashboard — Backend

Localização: `soc-dashboard/backend/`

| Ficheiro | Responsabilidade |
|---|---|
| `app/main.py` | Aplicação FastAPI principal (v3.0.0). Define middleware CORS, regista os routers de API e expõe endpoints directos compatíveis com a extensão Chrome: `POST /api/v1/analysis/cve`, `/api/v1/analysis/siem`, `/api/v1/analysis/chat`. Inclui também `GET /api/agent1/reports`, `/api/agent2/reports` e `/api/graph/state`. |
| `app/api/siem.py` | Endpoint REST para análise de alertas SIEM. `POST /api/v1/siem/analyze` — recebe um alerta JSON e devolve análise LLM. `GET /api/v1/siem/mock` — alerta de teste. |
| `app/api/analysis.py` | Endpoint de análise combinada. `POST /api/v1/analysis/360` — recebe lista de CVE IDs + alerta SIEM opcional e devolve análise LLM para cada um. |
| `app/api/cve.py` | Endpoints CVE. `GET /api/v1/cve/{cve_id}/raw` — dados brutos do NVD. `GET /api/v1/cve/{cve_id}/analyze?level=basic|intermediate|advanced` — análise 360° LLM. |
| `app/api/health.py` | `GET /api/v1/health` — devolve status, ambiente, provider LLM activo e modelo. |
| `app/core/config.py` | Settings Pydantic (`pydantic-settings`). Carrega `.env`, resolve `ACTIVE_LLM_MODEL` a partir de `LLM_PROVIDER2` (ollama/anthropic/openai). Mantém `LLM_PROVIDER` em sync para código legacy. |
| `app/services/llm_service.py` | Serviço LLM do backend, via **LiteLLM**. Suporta Ollama, Anthropic e OpenAI/LiteLLM. Expõe `analyze_cve()`, `analyze_siem_alert()` e `chat()`. |
| `app/services/cve_service.py` | Integração com NVD API v2. Busca e parseia CVEs com cache em disco (`data/cve_cache/`, TTL configurável). |
| `app/core/config.py` | Settings Pydantic (`pydantic-settings`). Carrega `.env`, resolve `ACTIVE_LLM_MODEL` a partir de `LLM_PROVIDER2` (ollama/anthropic/openai). Mantém `LLM_PROVIDER` em sync para código legacy. |
| `server/sse_server.py` | Servidor de Server-Sent Events (SSE) standalone (Python `http.server`). Serve também os ficheiros estáticos do frontend (`FRONTEND_DIST_DIR`). Emite eventos em tempo real para o browser. Endpoint `POST /ingest` recebe eventos dos agentes. |
| `server/server_texer.py` | Servidor Flask para compilação de relatórios LaTeX em PDF. Expõe `GET /render-pdf?file=<nome>`, `POST /render`, `GET /list` e `GET /debug`. Invoca `pdflatex` em directório temporário com N passes configuráveis. Requer TeX Live ou MiKTeX instalado. |

### 4.4 SOC Dashboard — Frontend

Localização: `soc-dashboard/frontend/src/`

| Ficheiro/Pasta | Responsabilidade |
|---|---|
| `main.ts` | Ponto de entrada da aplicação frontend. Inicializa o store, bootstrap dos componentes e subscrição ao SSE stream. |
| `components/alert_timeline.ts/.css` | Componente de timeline de alertas. Visualização cronológica dos alertas activos, agrupados por janela temporal e categoria CISO. Suporta zoom, filtragem e drill-down. |
| `components/windows_panel.ts/.css` | Painel de janelas temporais activas. Exibe o estado de cada sliding window com score acumulado, categoria dominante e estado CISO em tempo real. |
| `components/agent2.ts/.css` | Renderer de intelligence cards do Agent 2. Exibe os cards estruturados com contexto táctico, TTPs, recomendações e flags regulatórias. |
| `components/graph_viz.ts/.css` | Visualização interactiva do grafo de hipóteses. Renderiza o DAG de relações entre alertas, probabilidades e progressão kill chain. |
| `components/slice.ts/.css` | Componente de slice/filtro para segmentação de alertas por categoria CISO, severidade, fonte ou janela temporal. |
| `components/footer.ts` | Rodapé da aplicação com estado do sistema, última actualização e links de referência regulatória. |
| `core/store.ts` | Store de estado global da aplicação (pattern Redux-like). Gere estado de alertas, clusters, cards e configuração de UI. |
| `core/types.ts` | Definições TypeScript de todos os tipos de dados: Alert, Cluster, Card, CisoCategory, KillChainPhase, etc. |
| `core/constants.ts` | Constantes da aplicação: Phase Map, limiares de score, categorias CISO, mapeamentos regulatórios. |
| `core/utils.ts` | Utilitários partilhados: formatação de timestamps, cálculo de scores, normalização de dados. |
| `core/logger.ts` | Logger estruturado para o frontend, com níveis de severidade e integração com o backend de logging. |
| `network/api.ts` | Cliente HTTP para comunicação com o backend FastAPI. Abstrai endpoints REST com tipagem TypeScript completa. |
| `network/persistence.ts` | Gestão de persistência local: cache de cards, histórico de alertas e preferências de utilizador. |
| `data/reports.ts` | Acesso e formatação de relatórios gerados pelo Agent 2, incluindo relatórios LaTeX e visualizações de grafo. |
| `styles/theme.css` | Tema global da aplicação: paleta de cores (mapeada para estados CISO), tipografia e variáveis CSS. |
| `boot/template.ts` | Templates de bootstrap e inicialização de componentes. |

### 4.5 SOC Dashboard — SSE Server

O servidor SSE (`sse_server.py`) implementa comunicação unidireccional do servidor para o browser, sem polling. Eventos emitidos:

| Evento SSE | Trigger | Payload |
|---|---|---|
| `new_cluster` | Agent 1 detecta novo cluster | `{cluster_id, ciso_category, score, state}` |
| `card_ready` | Agent 2 completa intelligence card | `{card_id, cluster_id, severity, regulatory_flags}` |
| `score_update` | Score acumulado de janela actualizado | `{window_id, delta_score, new_state}` |
| `noise_discarded` | Alerta descartado por ruído | `{alert_id, reason}` |
| `agent_health` | Heartbeat dos agentes | `{agent1_status, agent2_status, queue_depth}` |

### 4.6 Redshift Chrome Extension

Localização: `redshift-chrome-extension/src/`

Extensão Chrome (**RedShift CVE Agent** v1.1.0, Manifest V3). Tem duas funções principais: (1) scan automático de CVEs em páginas abertas (Kibana, SOC Dashboard) com highlight interactivo; (2) análise 360° de CVEs e alertas SIEM directamente no contexto do analista, via popup.

| Ficheiro | Responsabilidade |
|---|---|
| `manifest.json` | Manifesto V3. Permissões: `activeTab`, `storage`, `scripting`, `tabs`, `clipboardRead`. Host permissions para `localhost:8000` (backend FastAPI) e `localhost:5001` (SSE/frontend). Content scripts injectados em Kibana e no SOC Dashboard. |
| `background.ts` | Service worker. Na instalação, inicializa settings com `apiUrl: localhost:8000` e `socDashboard: localhost:5001`. Gere badge (contagem de CVEs detectados) e mensagens `CVE_DETECTED`, `CLEAR_BADGE`, `OPEN_WITH_CVE`, `WINDOW_CONTEXT_READY`. Não mantém conexão SSE persistente. |
| `content.ts` | Content script. Faz scan de CVEs no DOM via TreeWalker (regex `CVE-\d{4}-\d{4,}`) e injeta chips clicáveis com botão de análise. Recebe contexto de janela do dashboard via `window.postMessage` (`REDSHIFT_WINDOW_CONTEXT`) — ativado quando uma hipótese atinge ≥75% de probabilidade. |
| `popup.ts` | Lógica do popup: tab CVE Analyzer, tab SIEM Analyzer, tab Chat. Chama `POST /api/v1/analysis/cve`, `/api/v1/analysis/siem`, `/api/v1/analysis/chat` no backend. |
| `popup.html` | Estrutura HTML do popup. |
| `popup.css` | Estilos do popup, tema dark consistente com o SOC Dashboard. |

### 4.7 Módulos Raiz

| Ficheiro | Responsabilidade |
|---|---|
| `launcher.py` | Ponto de entrada global do sistema. Inicializa e orquestra todos os componentes: Agent 1, Agent 2, backend e SSE server. Gere ciclo de vida, sinais de shutdown e restart de componentes. |
| `shared_config.py` | Configuração partilhada entre todos os módulos. Carrega variáveis de `.env`, define parâmetros globais (sliding window size, limiares de score, modelo LLM, endpoints) e expõe constantes do Phase Map. |
| `ioc_extractor.py` | Extractor automático de Indicators of Compromise. Analisa alertas e relatórios para extrair IPs, domínios, hashes, URLs, CVEs e IOCs MITRE. Alimenta a extensão Chrome e enriquece cards do Agent 2. O Agent 2 (`analyzers.py`) importa-o com fallback inline caso não esteja disponível. |
| `projD.txt` | Ficheiro de especificação interna do projecto. |
| `Run.bat` | Script de arranque Windows. Inicializa ambiente virtual e lança `launcher.py`. |
| `.env` | Variáveis de ambiente (não incluído no repositório — ver secção Configuração). |

---

## 5. Modelo de Dados — Estrutura do Alerta

Cada alerta de entrada deve conter os seguintes campos:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `Number` | string | ✓ | Identificador único do alerta (ex: W101) |
| `TLP` | enum | ✓ | Classificação de partilha: white / green / amber / red |
| `ExternalId` | string | — | ID externo no SIEM de origem |
| `Priority` | enum | ✓ | info / low / medium / high / critical |
| `Severity` | enum | ✓ | low / medium / high / critical |
| `Status` | enum | ✓ | new / closed / in_progress |
| `Title` | string | ✓ | Título descritivo (usado em keyword matching) |
| `Source` | string | ✓ | Sistema de origem: SIEM / EDR / IDS / WAF / DLP... |
| `Category` | string | ✓ | Categoria primária de detecção (ver Phase Map) |
| `Type` | string | ✓ | Sub-tipo do evento (ver Phase Map) |
| `Tags` | list[string] | ✓ | Keywords para mapeamento secundário |
| `MitreAttack` | string | — | Técnica ATT&CK (ex: T1486) |
| `AffectedAsset` | string | ✓ | Asset ou range IP afectado |
| `Description` | string | ✓ | Descrição técnica (usado em keyword matching e LLM) |
| `Resolution` | string | — | `falsepositive` → descarte imediato |
| `IsNoiseAlert` | bool | ✓ | `true` → descarte imediato |
| `UseCaseTag` | string | — | Tag de use case ENISA |
| `SiemDetectionTime` | datetime | ✓ | Timestamp para sliding window |
| `AssignedAt` | datetime | — | Timestamp de atribuição |
| `Assignee` | string | — | userId e groupId do analista |

---

## 6. Kill Chain & Phase Map

O mapeamento primário (definido em `agent1/mappings.py`) traduz o par `(Category, Type)` para uma fase da Cyber Kill Chain com peso numérico:

| Category | Type (keywords aceites) | Fase Kill Chain | Peso (w) |
|---|---|---|---|
| `informationgathering` | scanning, reconnaissance, osint | **RECON** | 1 |
| `authentication` | login, brute force, credential stuffing | **INITIAL_ACCESS** | 3 |
| `execution` | script, command, powershell, malware | **EXECUTION** | 4 |
| `lateral_movement` | rdp, wmi | **LATERAL_MOVEMENT** | 5 |
| `persistence` | backdoor, registry | **PERSISTENCE** | 6 |
| `exfiltration` | data, data leak | **EXFILTRATION** | 7 |
| `impact` | ransomware, wiper, encryption, system | **IMPACT** | 8 |

> A progressão de pesos (1→3→4→5→6→7→8) reflecte a Cyber Kill Chain de Lockheed Martin: fases iniciais têm menor peso por serem mais comuns e menos indicativas de comprometimento severo; fases avançadas têm maior peso por indicarem que o atacante ultrapassou múltiplas barreiras defensivas.

---

## 7. Mapeamento Phase → Categoria CISO

Após determinação da fase kill chain, `agent1/mappings.py` mapeia para a categoria CISO primária:

| Fase Kill Chain | Categoria CISO |
|---|---|
| RECON | CISO-15 — Reconnaissance & Pre-Attack Intelligence |
| INITIAL_ACCESS | CISO-4 — Credential & Identity Compromise |
| EXECUTION | CISO-14 — Malware Infrastructure & Botnet Activity |
| PERSISTENCE | CISO-5 — Advanced Persistent Threats (APT) |
| LATERAL_MOVEMENT | CISO-5 — Advanced Persistent Threats (APT) |
| EXFILTRATION | CISO-3 — Data Exfiltration & Corporate Espionage |
| IMPACT | CISO-1 — Ransomware & Digital Extortion |

> As categorias CISO-2, 6, 7, 8, 9, 10, 11, 12, 13 e 16 são atingidas exclusivamente via mapeamento secundário por keyword matching (ver secção 12).

---

## 8. Modelo de Scoring e Estados CISO

O score de um cluster é a soma acumulada dos pesos das fases kill chain detectadas:

```
score = Σ w(fase_i)  para cada alerta_i no cluster
```

| Score | Estado CISO | Acção Recomendada |
|---|---|---|
| 0 | **RUIDO_OPERACIONAL** | Logging apenas |
| 1–2 | **RUIDO_OPERACIONAL** | Monitorização passiva |
| 3–4 | **ATIVIDADE_SUSPEITA** | Investigação L1/L2 |
| 5–9 | **INCIDENTE_SEGURANCA** | Resposta a incidentes |
| 10–14 | **INCIDENTE_GRAVE** | Escalada CSIRT |
| ≥ 15 | **CRITICAL_COMBINED_ATTACK** | Activação de crise |

---

## 9. Catálogo de Categorias CISO (16)

| ID | Categoria | ATT&CK Típico | Regulamento |
|---|---|---|---|
| CISO-1 | Ransomware & Digital Extortion | T1486, T1490 | NIS2 Art.23, GDPR Art.33 |
| CISO-2 | Destructive Operations & Wipeware | T1485, T1487 | NIS2 Art.23 |
| CISO-3 | Data Exfiltration & Corporate Espionage | T1041, T1048 | GDPR Art.33 |
| CISO-4 | Credential & Identity Compromise | T1110, T1558 | — |
| CISO-5 | Advanced Persistent Threats (APT) | T1047, T1021 | NIS2 Art.23 |
| CISO-6 | Supply Chain & Third-Party Compromise | T1195, T1199 | NIS2 Art.21, DORA |
| CISO-7 | Critical Service Disruption (DDoS) | T1498, T1499 | NIS2 Art.23 |
| CISO-8 | Social Engineering, Phishing & BEC | T1566, T1598 | — |
| CISO-9 | System & Application Vulnerability Exploitation | T1190, T1203 | NIS2 Art.21 |
| CISO-10 | Information Manipulation & Integrity Attacks | T1491, T1565 | — |
| CISO-11 | Insider Threats & Physical Security | T1078, T1052 | — |
| CISO-12 | Regulatory & Compliance Violations | T1562 | NIS2, GDPR, DORA |
| CISO-13 | Cryptojacking & Unauthorized Resource Abuse | T1496 | — |
| CISO-14 | Malware Infrastructure & Botnet Activity | T1071, T1059 | — |
| CISO-15 | Reconnaissance & Pre-Attack Intelligence | T1595, T1592 | — |
| CISO-16 | Outros (extensão futura) | — | — |

---

## 10. Lógica de Clustering do Agente 1

Implementada em `agent1/window_manager.py` e `agent1/hypothesis_graph.py`.

### Sliding Window (window_manager.py)

A janela deslizante é parametrizada via `shared_config.py` e define o intervalo temporal dentro do qual alertas são candidatos ao mesmo cluster. O `window_manager.py` mantém o estado de janelas activas, detecta pares de alertas com intervalos significativos (floating window triggers) e emite clusters quando os limiares são atingidos.

### Grafo de Hipóteses (hypothesis_graph.py)

O grafo de hipóteses modela relações causais entre alertas como um DAG (Directed Acyclic Graph):

```
W101 (RECON) ──► W103 (INIT_ACCESS) ──► W106 (EXEC) ──► W107 (LAT_MOV)
                                                    └──► W108 (LAT_MOV)
                                                               └──► W109 (PERS)
```

Cada aresta tem uma probabilidade de transição calculada pelo `probabilistic_classifier.py` com base em:
- Frequência histórica da transição entre as duas fases
- Intervalo temporal entre os alertas
- Sobreposição de assets afectados

### Princípio de múltiplos cards por janela

O Agente 1 produz um card por **cluster** (não por janela). Uma janela com múltiplas categorias CISO activas produz múltiplos cards independentes, cada um com o score acumulado da janela no momento de emissão.

---

## 11. Descarte de Ruído Operacional

Implementado em `agent1/main.py`, processado antes do mapeamento de fase:

```python
# Caminho 1 — Resolution flag
if alert.Resolution == "falsepositive":
    discard(alert)  # card LOW/Others/score 0

# Caminho 2 — IsNoiseAlert flag
if alert.IsNoiseAlert == True:
    discard(alert)  # card LOW/Others/score 0
```

---

## 12. Mapeamento Secundário via primary_ciso

Quando `(Category, Type)` não corresponde ao Phase Map principal, `agent1/mappings.py` aplica keyword matching sobre `Title`, `Tags` e `Description` para identificar a categoria CISO mais próxima.

| Exemplo | Category/Type | Keywords Match | Categoria | Fase Atribuída |
|---|---|---|---|---|
| Compliance violation | other/compliance | "compliance", "nis2", "gdpr" | CISO-12 | EXECUTION (score 4) |
| DDoS (versão original) | availability/ddos | "ddos", "denial_of_service" | CISO-7 | IMPACT (via primary_ciso) |

---

## 13. Sistema de Logging

Implementado em `core/logging.py`, com output para `logs/`:

| Ficheiro de Log | Conteúdo |
|---|---|
| `logs/app.log` | Log geral da aplicação — arranque, shutdown, eventos de sistema |
| `logs/agent1.log` | Operações do Agent 1 — clustering, scoring, descarte de alertas |
| `logs/agent2.log` | Operações do Agent 2 — análise LLM, geração de cards e relatórios |
| `logs/classification.log` | Decisões de classificação — Phase Map lookups, keyword matches, score calculations |
| `logs/execution.log` | Trace de execução — timestamps de entrada/saída de cada módulo |
| `logs/performance.log` | Métricas de performance — latência de clustering, tempo de resposta LLM, throughput |
| `logs/errors.log` | Erros e excepções — stack traces, falhas de conexão, erros de parsing |

---

## 14. Instalação

### Pré-requisitos

| Dependência | Versão mínima | Notas |
|---|---|---|
| Python | 3.10+ | f-strings estruturais, match/case |
| Node.js | 18 LTS+ | Para o frontend Vite/TypeScript |
| npm | 9+ | Gestão de pacotes frontend |
| Git | 2.30+ | — |
| Chrome/Chromium | 109+ | Para a extensão (Manifest V3) |
| TeX Live / MiKTeX | — | Necessário para `server_texer.py` compilar PDFs (`pdflatex`) |

### 1. Clonar o repositório

```bash
git clone https://github.com/<username>/TesteDeep5.git
cd TesteDeep5
```

### 2. Ambiente Python

```bash
# Criar e activar ambiente virtual
python3 -m venv env
source env/bin/activate          # Linux/macOS
env\Scripts\Activate.ps1         # Windows PowerShell

# Instalar dependências Python
pip install -r requirements.txt
```

### 3. Dependências Frontend

```bash
cd soc-dashboard/frontend
npm install

cd ../../redshift-chrome-extension
npm install
```

### 4. Configuração (`.env`)

```bash
cp .env.example .env
# editar .env com os valores do ambiente (ver secção 16)
```

### 5. Verificar instalação

```bash
# Python
python -c "import fastapi, uvicorn, httpx; print('Backend OK')"

# Frontend
cd soc-dashboard/frontend && npm run build
```

---

## 15. Dependências

### Python (`requirements.txt`)

```
# Core
fastapi>=0.100.0          # framework API REST
uvicorn>=0.23.0           # servidor ASGI
httpx>=0.24.0             # cliente HTTP async
pydantic>=2.0.0           # validação de dados e settings
pydantic-settings>=2.0.0  # Settings com .env (usado em soc-dashboard/backend)
litellm>=1.0.0            # abstracção multi-provider LLM (backend + agent 2)
loguru>=0.7.0             # logging no backend (cve_service, llm_service)
flask>=3.0.0              # server_texer.py (compilação LaTeX)
flask-cors>=4.0.0         # CORS no server_texer.py

# Agent 1
python-dateutil>=2.8.2    # parsing de timestamps ISO 8601
networkx>=3.1             # grafos (hypothesis_graph.py)
numpy>=1.24.0             # operações probabilísticas

# Agent 2
openai>=1.0.0             # cliente LLM (compatível com OpenAI API)
jinja2>=3.1.0             # templates para latex_generator.py
matplotlib>=3.7.0         # visualizações graph_reporter.py

# Utilitários
pyyaml>=6.0               # configuração YAML
python-dotenv>=1.0.0      # carregamento de .env
rich>=13.0                # output formatado no terminal

# Testes
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
```

### Frontend (`soc-dashboard/frontend/package.json`)

```json
{
  "devDependencies": {
    "typescript": "^5.4.5",
    "vite": "^5.2.11"
  }
}
```

> O frontend não tem dependências de runtime declaradas em `package.json` — usa apenas TypeScript e Vite como ferramentas de build. D3, eventsource ou outras libs são carregadas via CDN ou implementadas nativamente.
```

### Chrome Extension (`redshift-chrome-extension/package.json`)

```json
{
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/chrome": "^0.0.246"
  }
}
```

---

## 16. Configuração

O sistema é configurado através de `.env` (raiz do projecto) e `shared_config.py`.

### Variáveis de ambiente (`.env`)

```dotenv
# ── LLM (Agent 2) ─────────────────────────────────────────────
# Provider: "ollama" | "anthropic" | "openai" (via LiteLLM) | "none"
LLM_PROVIDER2=ollama

# Ollama (local)
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-haiku-20240307

# OpenAI / LiteLLM
OPENAI_API_KEY=sk-...
LITELLM_MODEL2=gpt-4o

# ── Agent 1 ──────────────────────────────────────────
SLIDING_WINDOW_SECONDS=3600
MIN_CLUSTER_SCORE=1
NOISE_DISCARD_ENABLED=true

# ── Agent 2 ──────────────────────────────────────────
LATEX_OUTPUT_DIR=reports/agent2
GRAPH_OUTPUT_DIR=reports/agent2/graphs
LLM_QUALITY_MIN_SCORE=0.7

# ── Backend ───────────────────────────────────────────
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# ── SSE Server ────────────────────────────────────────
# Vite dev proxy aponta para localhost:5000
# Extensão Chrome usa socDashboard: localhost:5001
SSE_PORT=5000

# ── LaTeX/Texer Server ────────────────────────────────
TEXER_PORT=5002
TEXER_HOST=localhost
TEXER_COMPILE_TIMEOUT=60
TEXER_COMPILE_RUNS=2

# ── CVE Service ───────────────────────────────────────
NVD_API_KEY=...

# ── Logging ───────────────────────────────────────────
LOG_LEVEL=INFO
LOG_DIR=logs
```

---

## 17. Utilização

### Arranque completo (todos os componentes)

```bash
# Linux/macOS
source env/bin/activate
python launcher.py

# Windows
Run.bat
```

### Arranque individual de componentes

```bash
# Só Agent 1
python agent1/main.py --input data/alerts.txt

# Só backend
cd soc-dashboard/backend
uvicorn app.main:app --reload --port 8000

# Só frontend (desenvolvimento)
cd soc-dashboard/frontend
npm run dev

# SSE server
python soc-dashboard/server/sse_server.py
```

### Build do frontend para produção

```bash
cd soc-dashboard/frontend
npm run build
# output em dist/ — servir via nginx ou backend FastAPI /static
```

### Build da extensão Chrome

```bash
cd redshift-chrome-extension
npm run build
# output em dist/ — carregar em chrome://extensions → "Load unpacked"
```

### Instalar extensão Chrome (modo developer)

1. Abrir `chrome://extensions`
2. Activar **Developer mode** (canto superior direito)
3. Clicar **Load unpacked**
4. Seleccionar `redshift-chrome-extension/dist/`

### Correr testes

```bash
# Todos os testes
pytest -v

# Com cobertura
pytest --cov=agent1 --cov=agent2 --cov-report=html

# Janela específica
pytest tests/test_window1.py -v
```

---

## 18. Dataset de Testes

O ficheiro `projD.txt` contém **37 alertas** — 33 de ataque distribuídos por 5 grupos lógicos e 4 alertas de ruído descartados antes de qualquer clustering — cobrindo as 7 fases da kill chain, as 15 categorias CISO operacionais e ambos os caminhos de descarte (`Resolution=falsepositive` e `IsNoiseAlert=true`). O período simulado é 2026-04-24.

| Grupo lógico | Alertas | Fases previstas | Hipótese esperada |
|---|---|---|---|
| Grupo 1 | W101–W104 | RECON, INITIAL_ACCESS | APT |
| Grupo 2 | W105–W113 | EXECUTION→PERSISTENCE→LAT_MOV→EXFIL→IMPACT | Ransomware |
| Grupo 3 | W114–W116 | IMPACT (extensão adaptiva) | — (sub-janela) |
| Grupo 4 | W201–W206 | INITIAL_ACCESS→EXECUTION→LAT_MOV | Credential |
| Grupo 5 | W301–W304 | RECON, INITIAL_ACCESS | Credential |
| Grupo 6 | W401–W402 | RECON ×2 | Reconhecimento (ruído) |
| Grupo 7 | W501–W505 | EXECUTION→PERSISTENCE→IMPACT | Ransomware |
| Ruído | N101–N104 | — | Descartados |

> **Nota:** Os grupos lógicos acima representam a estrutura do dataset. As janelas efectivamente criadas pelo sistema dependem do modo de janelamento (adaptivo vs. fixo) — ver secção 19.

---

## 19. Resultados de Validação Experimental (modo adaptivo)

Execução de referência: **2026-05-25**, modo adaptivo (`Tw` variável por fase: RECON 5min, INITIAL_ACCESS 10min, EXECUTION 15min, PERSISTENCE 15min, LATERAL_MOVEMENT 20min, EXFILTRATION 25min, IMPACT 30min; extensão +5min/alerta adicional, hard cap 60min). LLM: `claude-haiku-4-5-20251001`, θ = 0,85.

O pipeline produziu **8 janelas fechadas** e **4 Relatórios de Inteligência**.

### 19.1 Janelas fechadas

| Intervalo | Alertas | Score | Pr | Resultado |
|---|---|---|---|---|
| 09:00–09:05 | W101–W104 | 4 | 88% | **APT (HIGH)** — relatório gerado |
| 09:07–09:57 | W105–W113 | 30 | 88% | **Ransomware (CRITICAL)** — relatório gerado |
| 09:29–10:14 | W114–W116 | 8 | 75% | Timeout — sem relatório (sub-janela adaptiva) |
| 11:00–11:25 | W201–W206 | 12 | 93% | **Credential (HIGH)** — relatório gerado |
| 13:00–13:05 | W301–W302 | 4 | 63% | Timeout — sem relatório |
| 13:08–13:18 | W303–W304 | 3 | 70% | Timeout — sem relatório |
| 15:00–15:05 | W401–W402 | 1 | 85% | **Reconhecimento (LOW)** — relatório gerado |
| 16:00–16:45 | W501–W505 | 18 | 80% | Finalizado pelo operador — sem relatório* |

*A janela 16:00–16:45 (Ransomware, S=18, Pr=80%) foi fechada pelo botão **Finish** antes de atingir θ. O `Finish` encerra janelas no frontend mas não invoca o `GraphReporter` — ver secção 21.

### 19.2 Relatórios de Inteligência gerados

| Relatório | Alertas | Score | Pr | Nível | Correcto |
|---|---|---|---|---|---|
| APT | W101–W104 (4) | 4 | 88% | HIGH | ✓ |
| Ransomware | W105–W113 (9) | 30 | 88% | CRITICAL | ✓ |
| Credential | W201–W304 (14) | 12 | 93% | HIGH | ✓ |
| Reconhecimento | W401–W402 (2) | 1 | 85% | LOW | ✓ |

> O relatório Credential acumulou alertas de múltiplas janelas (W201–W206 + W301–W304) por extensão adaptiva, atingindo Pr=93% com 14 alertas e progressão INITIAL_ACCESS→EXECUTION→LAT_MOV.

### 19.3 Tratamento de ruído

N101, N102 descartados por `Resolution=falsepositive`. N103, N104 descartados por `IsNoiseAlert=true`. Nenhuma janela aberta, nenhuma hipótese gerada.

### 19.4 Métricas de validação

| Métrica | Esperado | Observado |
|---|---|---|
| Relatórios gerados | 4 | 4 (100%) |
| Categoria CISO correcta | 4/4 | 4/4 (100%) |
| Nível de risco correcto | 4/4 | 4/4 (100%) |
| Alertas de ruído descartados | 4/4 | 4/4 (100%) |
| Janelas com relatório espúrio | 0 | 0 |
| Enriquecimento LLM activo | Sim | Sim (`claude-haiku-4-5`) |

---

## 20. Alinhamento Regulatório

### NIS2 Art.23 — Notificação de incidentes significativos

- **Prazo:** 24h notificação inicial, 72h notificação completa
- **Activado por:** CISO-1, 2, 3, 5, 7 em estados INCIDENTE_GRAVE ou CRITICAL_COMBINED_ATTACK

### GDPR Art.33 — Notificação de violação de dados pessoais

- **Prazo:** 72 horas após tomada de conhecimento
- **Activado por:** CISO-3 (exfiltração), CISO-1 com dados pessoais, alertas W111/W112 (HR payroll)

### DORA Art.17 — Reporte de incidentes TIC

- **Activado por:** CISO-6 (supply chain), CISO-12 (compliance), CISO-1 (impacto operacional — sector financeiro)

---

## 21. Limitações Conhecidas

1. **`Finish` não invoca o Agent 2** — o botão Finish do dashboard encerra janelas activas no frontend e regista classificações num log JSON, mas não despoleta o `GraphReporter`. Para gerar relatório de uma janela encerrada manualmente, o analista deve confirmar a hipótese individualmente antes de usar o Finish, ou o pipeline deve ser estendido para invocar o `GraphReporter` a partir do handler `_handle_finish` do `sse_server.py`.

2. **Sub-janelas adaptivas não previstas** — o modo adaptivo pode criar janelas adicionais com alertas não previstos no design do dataset (ex. W114–W116, resultante da extensão +5min/alerta dentro da janela IMPACT). Estas sub-janelas encerram por timeout se Pr < θ, sem relatório — comportamento correcto mas que pode surpreender em análise forense.

3. **Confirmação com n=1 alerta** — o sistema confirma hipóteses com Pr ≥ θ mesmo com evidência mínima (n=1, excepção Pr ≥ 0,97). Recomenda-se impor n ≥ 2 como condição necessária adicional para confirmação automática.

4. **Correlação cross-janela ausente** — o sistema não correlaciona clusters entre janelas temporais distintas. Alertas de dois ataques consecutivos podem ser fundidos numa janela com Pr artificialmente elevada (observado no modo fixo: WIN-1 ∪ WIN-2 com Pr=97%).

5. **W302 inconsistência semântica** — `Category: authentication / Type: brute force` descreve um e-mail BEC. Funciona para mapeamento INITIAL_ACCESS mas pode falhar com validação semântica estrita.

6. **CISO-16 reservada** — sem keyword mapping definido.

7. **LLM quality fallback** — quando `llm_quality.py` rejeita a resposta do LLM, o sistema cai para análise determinística que não produz narrative intelligence.

---

## 22. Referências

### Frameworks de Segurança
- MITRE ATT&CK: https://attack.mitre.org/
- Cyber Kill Chain (Lockheed Martin): https://www.lockheedmartin.com/en-us/capabilities/cyber/cyber-kill-chain.html
- ENISA Threat Landscape 2024: https://www.enisa.europa.eu/publications/enisa-threat-landscape-2024

### Regulamentação
- NIS2 (UE) 2022/2555: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2555
- GDPR Art.33: https://gdpr-info.eu/art-33-gdpr/
- DORA (UE) 2022/2554: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2554

### Tecnologias
- FastAPI: https://fastapi.tiangolo.com/
- Vite: https://vitejs.dev/
- NetworkX (grafos): https://networkx.org/
- FIRST TLP Standard: https://www.first.org/tlp/
- Chrome Extensions Manifest V3: https://developer.chrome.com/docs/extensions/mv3/

---

## Licença

MIT License — Copyright (c) 2026

---

*Desenvolvido no âmbito de investigação em cibersegurança operacional.*
*SOC automation · CISO-level threat intelligence · NIS2 · GDPR · DORA · MITRE ATT&CK · ENISA.*
