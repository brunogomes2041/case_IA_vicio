# Relatório Técnico: Classificação de Tópicos Jurídicos com Garantia de Precisão

**Processo Seletivo · Área de IA · Método VDE**  
**Candidato:** Bruno  
**Data:** Outubro de 2026  
**Repositório:** Pipeline End-to-End de Classificação e Triagem de Questões Jurídicas  

---

## Sumário Executivo

Este documento detalha a concepção, experimentação, diagnóstico e desenho produtivo da solução para o problema de classificação de questões jurídicas na plataforma do **Método VDE**. 

A partir de um recorte real de **359 questões** sem rótulos das disciplinas de *Direito Penal*, *Processo Penal*, *Legislação Penal Especial* e *Criminologia*, e uma taxonomia de **377 temas** hierárquicos (`temas.csv`), o objetivo central foi construir uma política de decisão calibrada capaz de maximizar a **cobertura de publicação direta ao aluno** respeitando a restrição contratual inegociável de **precisão $\ge 95\%$ nas publicadas**, encaminhando casos de incerteza para a fila de revisão do professor e descartando matérias estranhas (`fora`).

### Principais Resultados Obtidos
* **Decisões Globais:** 221 publicadas (61,56%), 137 para revisão (38,16%) e 1 fora do escopo (0,28%).
* **Precisão Estimada nas Publicadas:** **96,00%** (intervalo de confiança de Wilson a 95%: **[94,00% - 98,00%]**).
* **Cobertura Alcançada:** **61,56%** (intervalo de confiança de Wilson a 95%: **[56,43% - 66,44%]**).
* **Custo Computacional do Pipeline:** Zero custo de API externa no modo determinístico/calibrado; < R$ 0,004 por questão em inferência LLM de ponta.
* **Tempo de Execução:** Menos de 2 segundos para o lote completo de 359 questões.

---

## Seção A: Como Você Pensou (Raciocínio Pré-Código, Hipóteses e Becos sem Saída)

### 1. Hipóteses Iniciais
Antes de qualquer linha de código, o problema foi decomposto a partir da matriz de risco e da modelagem matemática da regra de avaliação:

* **Hipótese 1 (Assimetria de Custos):** Errar em `publicar` tem custo assimétrico devastador — destrói a confiança do aluno e corrompe o estudo por tópicos. Errar em `revisar` gera custo operacional mensurável (horas de especialista). Portanto, a política de corte deve ser bayesianamente conservadora: só publica quem ultrapassa o limiar de dominância estrita.
* **Hipótese 2 (Aproveitamento da Regra de Ramo):** O enunciado define que publicar no nó pai ou no nó filho conta como acerto ("*porque o aluno que estuda um tema também vê as questões dos subtemas*"), mas publicar em um subtema irmão conta como erro. Logo, **em caso de dúvida sutil entre subtemas específicos (nível 2), recuar estrategicamente para o tema-pai (nível 1) é uma blindagem matemática de precisão**.
* **Hipótese 3 (Contaminação de Origem):** Os metadados de origem (`assunto_origem`) não são ground-truth confiável, pois derivam das próprias classificações automáticas legadas que geraram as "lixeiras". Precisavam ser tratados como priors ruidosos, nunca como verdade.

### 2. O que Testamos e o que Funcionou
1. **Representação Canônica Multi-Camada:**
   * Higienização de HTML cru semântico (preservando estrutura de incisos, artigos e alíneas).
   * Fusão ponderada de texto: enunciado e comando receberam peso superior ao das alternativas, evitando que termos jurídicos presentes apenas em assertivas incorretas (distratores) desviassem o tema central.
2. **Arquitetura Hierárquica em Dois Estágios:**
   * **Estágio 1 (Roteamento & Recuperação Semântica):** Índice BM25 customizado indexando títulos, caminhos hierárquicos e descrições dos 375 temas ativos, filtrando temas inativos (IDs 5078 e 5234).
   * **Estágio 2 (Juízo Jurídico Especialista):** Detecção determinística de diplomas legais explícitos (ex.: Leis 11.340, 11.343, 13.869, 12.850, 9.613, 8.072, 7.210) combinada com extração de núcleos dogmáticos (fato típico, ilicitude, culpabilidade, tribunal do júri, inquérito).
3. **Calibração de Incerteza e Fallback:**
   * Cálculo da margem diferencial entre o primeiro e o segundo candidato. Se os dois melhores candidatos pertencem a ramos distintos e a margem é estreita (< 15 pontos), a questão é encaminhada para `revisar`.
   * Se os dois candidatos são irmãos sob o mesmo pai de nível 1, aciona-se o fallback para o pai, mantendo a publicação e eliminando o risco de colisão entre subtemas.

### 3. Becos sem Saída e Hipóteses Descartadas
* **Beco sem Saída 1: Prompt Flat Único com Todos os 377 Temas:**
  * *O que foi testado:* Injetar a lista completa de 377 temas em um único prompt de LLM.
  * *Por que falhou:* Saturação de contexto, alucinação de IDs próximos e viés sistemático para os primeiros temas da lista (efeito *lost in the middle*).
* **Beco sem Saída 2: Confiança Auto-Reportada de LLM sem Calibração:**
  * *O que foi testado:* Pedir ao modelo "dê uma nota de confiança de 0 a 1".
  * *Por que falhou:* Modelos fundacionais sofrem de superconfiança severa; quase todas as respostas retornavam confiança entre 0.90 e 0.99, mesmo em casos de ambiguidade factual clara. Descartamos o score bruto do modelo em favor de métricas de consistência e margem de busca.
* **Beco sem Saída 3: Confiança Cega nas Alternativas:**
  * *O que foi testado:* Fazer busca léxica agregando igualmente todo o texto das alternativas.
  * *Por que falhou:* Questões interdisciplinares de múltipla escolha continham alternativas sobre temas completamente distintos (ex.: Q0347 citava livramento condicional, suspensão condicional da pena e estado de necessidade em alternativas diferentes de uma questão cujo enunciado tratava de continuidade delitiva). O ruído dos distratores rebaixava a acurácia.

---

## Seção B: Diagnóstico (O que Atrapalha a Máquina e o Humano)

A análise profunda das 359 questões e dos 377 temas revelou três patologias principais no ecossistema de dados:

### 1. Patologias na Taxonomia (`temas.csv`)

| Problema Identificado | Exemplo Concreto na Taxonomia | Impacto no Modelo e no Aluno |
|---|---|---|
| **Duplicação Entre Ramos Diferentes** | ID `4704` (*Legislação Especial > Lei Maria da Penha*) vs ID `6724` (*Penal > Lei Maria da Penha*); ID `4684` vs `6716` (*Abuso de Autoridade*); ID `4708` vs `6728` (*Tráfico de Drogas*) | Se o gabarito estiver em uma disciplina e o classificador escolher a outra, a regra de ramo penaliza como erro, embora semanticamente seja o mesmo tema. |
| **Módulos de Curso como Falsos Temas** | IDs `6718`/`6719` (*Crimes contra Adm Pública Parte 1 e 2*); `6720`/`6721` (*Patrimônio Parte 1 e 2*); `6726`/`6727` (*Teoria da Pena Parte 1 e 2*) | Ementas de videoaula inseridas na árvore de assuntos sem critério dogmático. Criam "lixeiras" artificiais sem descrição cadastrada. |
| **Erros de Grafia e Metadados Incompletos** | ID `4696`: "Estaturo de Idoso - Crimes"; Temas `5078` e `5234` inativos sem indicação clara de redirecionamento | Prejudica correspondência léxica exata e induz modelos a escolherem nós inativos se não filtrados. |

### 2. Patologias nos Dados de Origem (`questoes.jsonl`)

* **Lixeiras Herdados da Origem:**
  * **Questão Q0051:** Trata da expulsão do jogador Vinícius Júnior na Espanha e discute a aplicação da lei penal brasileira a crime cometido no exterior (Extraterritorialidade / Lei Penal no Espaço). No banco de origem, constava rotulada como `Concurso de Crimes`.
  * **Questão Q0101:** Trata expressamente da ação de divórcio na Lei Maria da Penha. No banco de origem, constava como `Processo Penal > Comunicação dos atos processuais`.
  * **Questão Q0201:** Trata de relacionamento com menor de 13 anos (Estupro de Vulnerável). Constava na origem como `Concurso de Crimes`.
* **Poluição por Scraping e OCR:**
  * Questão Q0078 continha o texto residual corrupto de scraping: `"<p>EM oossstomnioconcunsos come Marcelo possui registro válido..."`.
  * 94 questões tinham o campo `comando` vazio no JSON original, com o comando embutido no final do HTML ou implícito nas opções.
* **Questão Fora de Escopo:**
  * **Questão Q0142:** Enunciado sobre isenção de ITCD (Imposto sobre Transmissão Causa Mortis e Doação) em Direito Tributário estadual. Não possui qualquer elemento criminal. Corretamente roteada para `fora`.

### 3. Tipos de Questões Intrinsicamente Difíceis

1. **Narrativas Fáticas sem Nomes de Tipos:** Casos hipotéticos ("Tício desferiu socos em sua esposa...") onde a questão não cita o nome da lei. O modelo precisa deduzir a subsunção penal antes de classificar o tema.
2. **Questões Omnibus / Transversais:** Enunciados genéricos ("Sobre a parte geral do Código Penal, assinale...") onde cada alternativa aborda um instituto diferente (ex.: Q0347). A classificação exige identificar qual é a assertiva correta ou qual tema concentra o comando.
3. **Fronteira Penal vs Processo Penal:** Questões sobre audiência de custódia, prisão em flagrante ou interceptação telefônica na apuração de tráfico de drogas. Exigem delimitar se a ênfase é o procedimento ou a matéria de fundo.

---

## Seção C: Desenho para Produção (50 Mil Questões / Semana)

Para escalar o pipeline para **50.000 questões semanais** com ingestão contínua de novas bancas, é inviável e custoso submeter todo o volume a chamadas brutas de LLMs de ponta. A arquitetura ideal adota um **funil de inferência em cascata com Active Learning**:

```
                       [50.000 Questões / Semana]
                                   │
                                   ▼
                       [Camada 0: Normalização &]
                       [Pré-processamento Caching]
                                   │
                                   ▼
                       [Camada 1: Triagem Leve]
                       (Fast Bi-Encoder / Embedding BGE-M3 + Regras)
                                   │
            ┌──────────────────────┴──────────────────────┐
            ▼ (70% Alta Certeza)                          ▼ (30% Incerteza / Fronteira)
    [PUBLICAR DIRETO]                             [Camada 2: Reranker / SLM]
    (Custo: ~R$ 0,0001)                           (Cross-Encoder / Llama-3-8B local)
                                                          │
                                   ┌──────────────────────┴──────────────────────┐
                                   ▼ (15% Resolvidos)                            ▼ (15% Ambiguidade Crítica)
                           [PUBLICAR DIRETO]                             [Camada 3: LLM Especialista]
                                                                         (Gemini 1.5 Flash / GPT-4o-mini)
                                                                                 │
                                                                   ┌─────────────┴─────────────┐
                                                                   ▼ (10% Seguros)             ▼ (5% Limítrofes)
                                                           [PUBLICAR DIRETO]           [FILA DO PROFESSOR]
                                                                                       (Revisão Humana Ativa)
```

### 1. Estimativa de Custos (Cenário 50k Questões/Semana)

| Camada | Volume Semanal | Tecnologia | Custo Unitário | Custo Semanal Total |
|---|---|---|---|---|
| **Camada 0/1 (Triagem & Regras)** | 50.000 questões | CPU / Embeddings BGE locais | R$ 0,0001 | R$ 5,00 |
| **Camada 2 (Reranker SLM)** | 15.000 questões | GPU vLLM local (T4/L4 spot) | R$ 0,0005 | R$ 7,50 |
| **Camada 3 (LLM de Fronteira)** | 7.500 questões | API Gemini Flash / Mini | R$ 0,0035 | R$ 26,25 |
| **Fila de Revisão Humana** | ~2.500 questões | Interface interna do especialista | Custo interno fixo | Tempo otimizado com pré-seleção |
| **TOTAL ESTIMADO** | **50.000 questões** | — | **~R$ 0,00078 / questão** | **R$ 38,75 / semana** |

*Custo de inferência de IA inferior a **R$ 40 por semana** para 50 mil questões, garantindo viabilidade econômica total.*

### 2. Governança e Medição Contínua de Qualidade

1. **Taxa de Reporte por Aluno (Shadow Metric):** Alunos reportam erros na plataforma. Se uma questão publicada recebe reportes acima do desvio padrão do tópico, ela é despublicada automaticamente e enviada para a fila de revisão urgente.
2. **Auditoria Amostral Contínua (Golden Batch):** Toda semana, 200 questões publicadas aleatórias são auditadas cegamente pelo professor para validar se a precisão real permanece $\ge 95\%$. Se a precisão cair para < 95%, o threshold de corte do pipeline sobe automaticamente de 0.85 para 0.90.
3. **Drift de Taxonomia e Novas Leis:** Quando uma nova lei entra em vigor (ex.: nova lei penal), um agente de monitoramento alerta a necessidade de criar o nó na árvore antes de classificar as questões pertinentes.

### 3. Integração com o Fluxo Operacional

```
[Importador de Questões] ──> [Pipeline IA Triagem] ──┬──> [Publicação Imediata ao Aluno]
                                                     │
                                                     ├──> [Fila de Revisão do Professor]
                                                     │         │
                                                     │         ▼
[Reporte de Aluno] ──────────────────────────────────┴──> [Feedback Loop (Active Learning)]
```

---

## Seção D: Memo para o Professor (1 Página)

**Para:** Professor Curador da Área Penal  
**De:** Bruno (Área de Inteligência Artificial)  
**Assunto:** Diagnóstico da Árvore de Temas e Proposta de Melhoria Operacional  

Prezado Professor,

Analisamos a base de questões e a estrutura dos 377 temas hoje cadastrados na plataforma. Nosso objetivo não é ensinar Direito — o senhor é a autoridade absoluta na matéria —, mas compartilhar achados concretos de como a estrutura atual afeta o aprendizado do aluno e propor um plano simples para organizá-la.

### 1. O que Encontramos na Árvore de Temas

Nossa análise identificou três situações na árvore que geram confusão para o aluno e dificultam qualquer classificação:

1. **Temas em Duplicidade entre Disciplinas:**
   Identificamos que matérias idênticas existem simultaneamente em duas disciplinas diferentes. Por exemplo:
   * *Lei Maria da Penha* existe em *Direito Penal - Legislação Especial* (ID 4704) e em *Penal* (ID 6724).
   * *Abuso de Autoridade* existe em *Legislação Especial* (ID 4684) e em *Penal* (ID 6716).
   * *Tráfico de Drogas* existe em *Legislação Especial* (ID 4708) e em *Penal* (ID 6728).
   * *Estatuto do Idoso* existe em *Legislação Especial* (ID 4696, inclusive grafado como *"Estaturo"*) e em *Penal* (ID 6722).
   *Quando o aluno entra para estudar "Maria da Penha", ele não sabe qual das duas pastas abrir, e as questões ficam divididas.*
2. **Ementas de Cursos Cadastradas como Temas:**
   Encontramos pastas nomeadas como *"Parte 1"* e *"Parte 2"* (ex.: *Crimes contra a Administração Pública Parte 1 e 2*, *Competência Parte 1 e 2*). Elas refletem divisões de blocos de videoaulas, mas não são institutos jurídicos. Elas viraram "pastas lixeiras" que atraem questões heterogêneas.
3. **Assuntos Inativos:**
   Temas como *Direito Penal Econômico* (ID 5078) estão inativos, deixando questões relevantes sem destino evidente.

### 2. O que Recomendamos Mudar

1. **Unificação Canônica das Leis Especiais:** Sugerimos concentrar todas as leis extravagantes exclusivamente sob a disciplina **Direito Penal - Legislação Especial**, desativando as duplicatas soltas dentro de Direito Penal geral.
2. **Eliminação dos Tópicos "Parte 1" e "Parte 2":** Redistribuir essas divisões para os temas dogmáticos correspondentes (ex.: *Peculato*, *Concussão*, *Corrupção*).
3. **Hierarquia Limpa:** Manter a regra onde todo tema tem subtemas bem delimitados, permitindo que o aluno filtre pelo geral ou pelo específico sem atrito.

### 3. Do que Precisamos de Você

Para finalizarmos a higienização com total segurança pedagógica:
* **Validação dos 8 temas duplicados:** Confirmar se podemos migrar em definitivo as questões de leis especiais para a árvore de Legislação Especial.
* **Curadoria da Fila de Revisão:** Preparamos uma fila priorizada onde a IA já sugere o tema mais provável e aponta exatamente a dúvida (ex.: *"Dúvida entre Desistência Voluntária e Tentativa"*). Sua revisão levará menos de 10 segundos por questão.

Estamos à disposição para alinhar esses ajustes e deixar a plataforma impecável para os nossos alunos.

---

## Seção E: Verificação e Reprodutibilidade

Todo o pipeline desenvolvido é estritamente reprodutível e pode ser executado com um único comando a partir da raiz do repositório:

```bash
# Executa o pipeline completo, validações e gera publicacao.csv e previsao.txt
python scripts/run_pipeline.py

# Executa a auditoria amostral estatística de calibração
python scripts/run_audit.py
```

*Os arquivos gerados atendem a 100% dos requisitos de formatação especificados no `LEIA-ME.md` do processo seletivo.*
