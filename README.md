# Amazon RE:Flow

<div align="center">

[![Site](https://img.shields.io/badge/🌐_Site-Online-000000?style=for-the-badge)](https://mechanical-josy-felipedev-3fef2e29.koyeb.app/)
[![Status](https://img.shields.io/badge/⚙️_Status-concluido-green?style=for-the-badge)]()

</div>


**Amazon RE:Flow** é um projeto de pesquisa e engenharia de dados que constrói um pipeline (ETL + NLP) para transformar *reviews* de produtos da Amazon em insights acionáveis. Conceito com foco em automação, reprodutibilidade e preparação de dados para visualização em dashboards (Looker Studio via Google Sheets).

**clique no botão [site/online] para acessar o site(pode levar ate 30 segundos para carregar).**

---

## 🧭 Visão
Transformar o grande volume de avaliações de consumidores em sinais claros para tomada de decisão: entender satisfação, detectar problemas recorrentes por produto/brand e extrair tópicos relevantes que guiem melhorias de produto e atendimento.

---

## ❓ Problemas
Plataformas de e-commerce produzem milhões de reviews em texto livre. Esses textos são valiosos, porém:

- Estão sujos e pouco padronizados;  
- Têm duplicatas e metadados inconsistentes;  
- Exigem processamento para métricas agregadas (sentimento, temas, evolução temporal).

**Amazon RE:Flow** resolve isso oferecendo um fluxo reprodutível que transforma CSVs de reviews em um conjunto limpo e enriquecido com análises de texto, pronto para alimentar dashboards e relatórios.

---

## 🎯 Objetivos do projeto

- Construir um pipeline confiável e auditável que execute: `extract → transform → load → analyze → export`.  
- Enriquecer cada review com: `clean_text`, `sentiment` (positive / neutral / negative) e `keywords`.  
- Persistir os dados (SQLite via SQLAlchemy) e gerar CSVs prontos para dashboards. 

---


## ⚙️ Como rodar (localmente sem docker)

### Requisitos
- Python 3.11 (recomendado)  
- pip, virtualenv (ou conda)  
- opcional: Docker

### Local (sem Docker)
```bash
# clonar
git clone https://github.com/<seu-usuario>/Amazon-RE-Flow.git
cd Amazon-RE-Flow

# criar venv e instalar
python -m venv .venv
source .venv/bin/activate   # unix/mac
# .venv\Scripts\activate     # windows
pip install -r requirements.txt

# rodar pipeline local (gera CSV e sqlite)
python -m src.main --source data/raw/reviews_sample.csv --out data/processed/reviews_clean.csv --to-db --db data/db/reviews.db

# rodar app (dev)
python -m src.app
# ou com gunicorn
gunicorn src.app:app --bind 0.0.0.0:8000
```

---

## 🐳 Como rodar com Docker

### Build (no root do repo)
    docker compose up --build

`abra localhost:8000 no navegador de sua preferencia`

---

## 📊 Como gerar gráficos

### 1) Usando a interface web 

1. Acesse o app (ex.: `http://localhost:8000` ou `https://mechanical-josy-felipedev-3fef2e29.koyeb.app/`).
2. Na seção **Overview / Insights**, os gráficos principais são renderizados automaticamente a partir dos dados carregados.
3. Para customizar, use o **Custom Chart Builder**:

   * `Metric`: escolha `by_product`, `by_sentiment`, `by_rating`, `by_keyword` ou `timeseries`.
   * `Chart type`: selecione `Bar`, `Horizontal Bar`, `Pie` ou `Line`.
   * `Top N`: número de itens (por exemplo, top 10).
   * Clique em **Generate** — o gráfico aparecerá na área abaixo.


---

## 📤 Como gerar CSV para Google Sheets / Looker Studio

### Gerar csv para dashboard
    1. No app clique em **Gerar CSV** (botão `Gerar CSV` na seção Export).
    2. Após processar, botão `Download CSV` aparecerá. Baixe o arquivo `reviews_for_dashboard.csv`.
    
<img alt="CSV-Download" src="/assets/csv-download.png"/>

### Fazer upload para Google Sheets
    1. Abra Google Sheets → `Arquivo` → `Importar` → `Upload` → selecione o CSV gerado.
    2. Escolha `Substituir planilha` ou `Inserir nova planilha` conforme preferir.

<img alt="google-sheets-dashboard" src="/assets/google-sheets-dashboard.png"/>


### Conectar Looker Studio

    1. No Looker Studio crie uma nova fonte de dados apontando para **Google Sheets** (escolha a planilha com o CSV importado).
    2. Construir painéis: filtros por `product`, `sentiment`, `rating`, intervalo de datas.
    3. Se preferir dados maiores e mais dinâmicos, use BigQuery (exporte CSV para GCS e depois importe para BQ) e conecte Looker Studio ao BigQuery.

<img alt="looker-studio-dashboard" src="/assets/looker-studio-dashboard.png"/>

---

## 📚 Estrutura do repositório (resumida)

```
.
├─ data/
│  ├─ raw/                # CSVs brutos (ex.: reviews_sample.csv)
│  ├─ processed/          # CSVs processados pelo pipeline
│  └─ db/                 # sqlite (reviews.db)
├─ src/
│  ├─ etl.py              # extração e transformação
│  ├─ nlp.py              # limpeza, sentiment, keywords
│  ├─ db.py               # persistência via sqlalchemy
│  └─ app.py              # API + endpoints para frontend
├─ frontend/              # HTML / CSS / JS estáticos do dashboard
├─ screenshots/           
├─ requirements.txt
├─ Dockerfile
├─ Procfile
└─ README.md
```

