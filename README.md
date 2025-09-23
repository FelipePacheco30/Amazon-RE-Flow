# Amazon RE:Flow

**Amazon RE:Flow** é um projeto de pesquisa e engenharia de dados que constrói um pipeline local (ETL + NLP) para transformar *reviews* de produtos da Amazon em insights acionáveis.  
Este repositório é o resultado de uma prova de conceito com foco em automação, reprodutibilidade e preparação de dados para visualização em dashboards (Looker Studio via Google Sheets).

---

## 🧭 Visão
Transformar o grande volume de avaliações de consumidores em sinais claros para tomada de decisão: entender satisfação, detectar problemas recorrentes por produto/brand e extrair tópicos relevantes que guiem melhorias de produto e atendimento.

---

## ❓ Problema que resolvemos
Plataformas de e-commerce produzem milhões de reviews em texto livre. Esses textos são valiosos, porém:
- Estão sujos e pouco padronizados;
- Têm duplicatas e metadados inconsistentes;
- Exigem processamento para métricas agregadas (sentimento, temas, evolução temporal).

**Amazon RE:Flow** resolve isso oferecendo um fluxo reprodutível que transforma CSVs de reviews em um conjunto limpo e enriquecido com análises de texto, pronto para alimentar dashboards e relatórios.

---

## 🎯 Objetivos do projeto
- Construir um pipeline confiável e auditável que execute: *extract → transform → load → analyze → export*.  
- Enriquecer cada review com: `clean_text`, `sentiment` (positive/neutral/negative) e `keywords`.  
- Persistir os dados localmente (SQLite via SQLAlchemy) e gerar CSVs prontos para dashboards.  
- Fornecer documentação e etapas claras para futura migração para nuvem.

---

## 📦 Dataset
Fonte: coleções públicas de *Amazon Consumer Reviews* (Datafiniti / Kaggle).  
Características importantes:
- Contém metadados do produto (ASINs, brand, categorias) e campos de review (`reviews.text`, `reviews.rating`, `reviews.date`, `reviews.id`).  
- O pipeline unifica, limpa e padroniza esses campos, produzindo um dataset consolidado.

---

## 🔬 Metodologia (nível alto)
1. **Ingestão (Extract):** leitura de CSV(s) brutos.  
2. **Limpeza (Transform):** normalização de nomes de coluna, remoção de duplicatas, preenchimento/tratamento de nulos, padronização de datas.  
3. **Enriquecimento (NLP):** limpeza de texto (remoção de URLs, emojis e ruído), análise de sentimento (VADER ou similar), extração de palavras-chave por review.  
4. **Persistência (Load):** armazenamento em SQLite para consultas e integridade; exportação de CSV para Google Sheets.  
5. **Visualização:** dashboards no Looker Studio com métricas agregadas e exploratórias.

---

## 🧠 Insights esperados / Métricas
- Distribuição de sentimento por produto/brand.  
- Média e variação de rating ao longo do tempo.  
- Tópicos/keywords mais frequentes por categoria de produto.  
- Detecção de reviews com alto *helpfulness* (quando disponível).  

Esses insumos suportam decisões como priorização de correções, identificação de produtos problemáticos e melhoria de copy/descrição.

---

## ⚖️ Ética, privacidade e limitações
- **Privacidade:** dados de reviews públicos são analisados, mas consideramos anonimização de `username` e remoção de PII se for necessário para divulgação.  
- **Bias e representatividade:** amostras podem refletir vieses (ex.: mais reviews para produtos populares). As conclusões devem considerar esse viés.  
- **Limitação técnica:** a versão atual é local e visa eficiência em máquinas modestas; modelos mais avançados (transformers) estão fora do escopo inicial por custo computacional.

---

## 🚀 Resultados entregáveis
- Dataset limpo e enriquecido: `data/processed/reviews_clean.csv`.  
- Banco local SQLite com tabela `reviews`.  
- CSV para dashboard: `data/export/reviews_for_dashboard.csv`.  
- Documentação e roteiro de migração para nuvem (GCS → BigQuery).  
- Looker Studio configurado apontando para o Google Sheet com os dados exportados.

---

## 🛣 Roadmap / Evolução futura
**Curto prazo**
- Melhorar extração de keywords (phrase detection).  
- Adicionar testes automatizados e CI básico.

**Médio prazo**
- Dockerizar pipeline e criar workflow para execução periódica.  
- Automatizar upload para Google Sheets (ou usar BigQuery para dashboards maiores).

**Longo prazo**
- Migrar análise de sentimento para modelos mais sofisticados (fine-tuned transformers) e suportar streaming de reviews em tempo real.

---

## 🧩 Público-alvo
- Equipes de produto/ops buscando entender feedback do usuário.  
- Pesquisadores que querem um pipeline reprodutível para análises textuais.  
- Desenvolvedores que desejam um template de ETL local com NLP integrado.

---

## 🧑‍🤝‍🧑 crédito
- Inspirado por datasets públicos (Datafiniti/Kaggle) e práticas padrão de engenharia de dados.
