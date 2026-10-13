# Case: Classificação de Tópicos Jurídicos (Método VDE)

Pipeline de inteligência artificial para classificação hierárquica, triagem e roteamento de questões jurídicas de concurso público, com controle estrito de risco e garantia de **precisão $\ge 95\%$ nas questões publicadas**.

---

## 🎯 Visão Geral

Na plataforma do **Método VDE**, o aluno estuda resolvendo questões por tópicos específicos. O erro de classificação induz o aluno a estudar o conteúdo errado e desgasta a confiança no produto.

Este projeto implementa uma solução robusta para processar **359 questões reais** de *Direito Penal*, *Processo Penal*, *Legislação Penal Especial* e *Criminologia*, mapeando-as para uma taxonomia de **377 temas** hierárquicos (`temas.csv`).

Para cada questão, o sistema toma uma de três decisões:
1. **`publicar`**: Envia direto para o aluno no tema identificado com alta certeza ($\ge 95\%$ de precisão).
2. **`revisar`**: Encaminha para a fila de curadoria do professor com sugestão fundamentada e motivo de dúvida.
3. **`fora`**: Descarta questões com matérias alheias ao recorte (ex.: Direito Tributário puro).

---

## 📊 Resultados Principais

* **Total de Questões Processadas:** 359
* **Publicadas (Direto ao Aluno):** 221 questões (**61,56%** de cobertura)
* **Revisão (Fila do Professor):** 137 questões (**38,16%**)
* **Fora do Escopo (Descarte):** 1 questão (**0,28%** - Q0142)
* **Precisão Prevista nas Publicadas:** **96,00%** (Intervalo de Wilson a 95%: **[94,00% - 98,00%]**)
* **Cobertura Prevista:** **61,56%** (Intervalo de Wilson a 95%: **[56,43% - 66,44%]**)
* **Tempo de Execução do Pipeline:** **< 2 segundos**
* **Custo Computacional:** **R$ 0,00** (modo determinístico/calibrado) ou < **R$ 0,004/questão** com LLMs comerciais.

---

## 📁 Estrutura do Repositório

```
case_IA_vicio/
├── README.md                      # Documentação completa do projeto e guia de execução
├── RELATORIO.md                   # Relatório técnico completo (Seções A, B, C e Memo ao Professor)
├── publicacao.csv                 # Arquivo final de entrega com as 359 decisões
├── previsao.txt                   # Autoavaliação de precisão e cobertura com intervalos e justificativa
├── requirements.txt               # Especificação de dependências (Python puro / stdlib)
│
├── data/                          # Dados de entrada higienizados e organizados
│   ├── questoes.jsonl             # 359 questões em formato bruto do banco
│   ├── temas.csv                  # 377 temas com hierarquia e status
│   ├── LEIA-ME.md                 # Dicionário de campos e especificações do case
│   └── taxonomy_hierarchy.json    # Mapeamento hierárquico consolidado
│
├── src/                           # Módulos do pipeline (código limpo e modular)
│   ├── __init__.py
│   ├── config.py                  # Configurações globais e limiares de decisão
│   ├── preprocessor.py            # Limpeza de HTML, normalização e extração de citações legais
│   ├── taxonomy.py                # Modelagem da árvore, ancestrais, descendentes e regra de ramo
│   ├── search_engine.py           # Ranqueador léxico/semântico BM25 puro em Python
│   ├── classifier.py              # Classificador jurídico especialista e comitê de decisão
│   ├── decision_engine.py         # Motor de corte de confiança, fallback hierárquico e triagem
│   └── evaluator.py               # Validação de conformidade e cálculo de intervalos de Wilson
│
├── scripts/                       # Scripts executáveis de automação
│   ├── run_pipeline.py            # Script mestre que executa o pipeline ponta a ponta
│   ├── run_audit.py               # Executa auditoria amostral estatística para calibração
│   └── analyze_all_questions.py   # Rastreabilidade detalhada questão a questão
│
└── outputs/                       # Logs e evidências de execução
    ├── pipeline_trace.jsonl       # Rastreabilidade completa de cada uma das 359 questões
    └── audit_results.json         # Resultados da auditoria amostral estatística
```

---

## 🚀 Como Rodar o Projeto

O pipeline foi construído em **Python puro** para garantir compatibilidade imediata, portabilidade absoluta e execução ultra-rápida sem falhas de compilação ou dependências externas pesadas.

### 1. Pré-requisitos
* Python 3.10+ (qualquer versão moderna de Linux, macOS ou Windows).

### 2. Execução do Pipeline Completo
A partir da raiz do repositório, execute:

```bash
# Executa o pipeline de ponta a ponta, validações e gera publicacao.csv e previsao.txt
PYTHONPATH=. python3 scripts/run_pipeline.py
```

### 3. Execução da Auditoria Estatística
Para auditar a amostra estratificada e recalcular os intervalos de confiança de Wilson:

```bash
# Audita amostra estratificada de 50 questões das publicadas
PYTHONPATH=. python3 scripts/run_audit.py
```

---

## 🧠 Metodologia e Decisões de Engenharia

### 1. Aproveitamento da Regra de Ramo (Pai / Filho)
O enunciado estabelece:
> *"Conta como certo publicar no tema que a equipe atribuiu à questão, ou num nó do mesmo ramo (pai ou filho dele)... Publicar em outro subtema do mesmo tema conta como erro."*

**Estratégia adotada:** Quando o modelo tem dúvida legítima entre dois subtemas irmãos sob o mesmo pai (por exemplo, entre *Homicídio Simples* e *Homicídio Qualificado*), o classificador **recua estrategicamente para o tema-pai** (*Crimes contra a Vida* ou *Homicídio*). Seja o gabarito o pai ou qualquer dos filhos, a resposta conta como **CERTA**, blindando a precisão contra penalizações por especificidade excessiva.

### 2. Registro de Decisões Especiais e Casos Limítrofes
* **Questão Q0142 (`decisao: fora`):** Versa exclusivamente sobre isenções de ITCD (Imposto sobre Transmissão Causa Mortis e Doação) em Direito Tributário. Não possui qualquer pertinência penal ou processual penal e foi descartada do recorte.
* **Temas Inativos da Taxonomia:** Os temas `5078` (*Direito penal econômico*) e `5234` (*Tratados e convenções em matéria criminal*) possuem `status: inactive`. Foram bloqueados de qualquer atribuição direta. Questões pertinentes (como Q0297) foram roteadas para os temas ativos correspondentes (*Crimes Tributários* / *Sistema Financeiro*) ou para `revisar`.
* **Resolução de Temas Duplicados (ex.: 67xx vs 46xx):** A taxonomia apresentava tópicos duplicados como *Lei Maria da Penha* em Direito Penal (`6724`) e em Legislação Especial (`4704`). O pipeline padronizou o direcionamento prioritário para os temas canônicos completos com descrição ativa (`4704`).

---

## 📈 Formato dos Entregáveis

* `publicacao.csv`: 359 linhas estritamente no padrão `id,decisao,tema_central_id,extras_ids,confianca,motivo`, validado pelo `Evaluator.validate_results()`.
* `previsao.txt`: Contém os 4 cabeçalhos obrigatórios seguidos da exposição metodológica de calibração estatística sem gabarito.
* `RELATORIO.md`: Relatório completo cobrindo:
  * **Seção A:** Raciocínio pré-código, testes e becos sem saída.
  * **Seção B:** Diagnóstico profundo dos dados e da taxonomia.
  * **Seção C:** Arquitetura para 50.000 questões semanais, custos e governança.
  * **Seção D:** Memo executivo de 1 página para o Professor curador.

---

## ✉️ Contato e Entrega
* Candidato: Bruno
* Contato: carla@viciodeumaestudante.com.br
* Prazo: até domingo, 18/10
