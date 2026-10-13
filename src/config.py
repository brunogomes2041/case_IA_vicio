"""
Configurações centrais do projeto de classificação de tópicos.
"""
from pathlib import Path

# Diretórios principais
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Arquivos de dados
QUESTOES_PATH = DATA_DIR / "questoes.jsonl"
TEMAS_PATH = DATA_DIR / "temas.csv"
LEIAME_PATH = DATA_DIR / "LEIA-ME.md"

# Arquivos de saída
PUBLICACAO_CSV_PATH = BASE_DIR / "publicacao.csv"
PREVISAO_TXT_PATH = BASE_DIR / "previsao.txt"
RELATORIO_MD_PATH = BASE_DIR / "RELATORIO.md"
TRACE_OUTPUT_PATH = OUTPUTS_DIR / "pipeline_trace.jsonl"
AUDIT_OUTPUT_PATH = OUTPUTS_DIR / "audit_results.json"

# Hiperparâmetros de decisão e calibração
# Limiar para considerar publicação segura (garantir precisão >= 95%)
CONFIDENCE_THRESHOLD_PUBLISH = 0.85

# Margem mínima de pontuação em relação ao segundo candidato de ramo diferente
MARGIN_THRESHOLD_DIFF_BRANCH = 0.15

# Disciplinas válidas na árvore
VALID_DISCIPLINES = {
    "Penal",
    "Processo Penal",
    "Direito Penal - Legislação Especial",
    "Criminologia",
}
