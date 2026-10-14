"""Pacote principal do pipeline de classificação de tópicos jurídicos.
"""

from src.config import (
    CONFIDENCE_THRESHOLD_PUBLISH,
    DATA_DIR,
    OUTPUTS_DIR,
    PREVISAO_TXT_PATH,
    PUBLICACAO_CSV_PATH,
    QUESTOES_PATH,
    RELATORIO_MD_PATH,
    TEMAS_PATH,
)
from src.decision_engine import ClassificationResult, DecisionEngine
from src.evaluator import Evaluator, wilson_score_interval
from src.preprocessor import Question, QuestionPreprocessor
from src.search_engine import SearchEngine
from src.taxonomy import Taxonomy, TopicNode

__all__ = [
    "Taxonomy",
    "TopicNode",
    "Question",
    "QuestionPreprocessor",
    "SearchEngine",
    "DecisionEngine",
    "ClassificationResult",
    "Evaluator",
    "wilson_score_interval",
    "CONFIDENCE_THRESHOLD_PUBLISH",
    "DATA_DIR",
    "OUTPUTS_DIR",
    "QUESTOES_PATH",
    "TEMAS_PATH",
    "PUBLICACAO_CSV_PATH",
    "PREVISAO_TXT_PATH",
    "RELATORIO_MD_PATH",
]

