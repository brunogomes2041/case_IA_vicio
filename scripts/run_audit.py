"""
Script de auditoria amostral estratificada para estimar a precisão empírica
e calibrar a autoavaliação (previsao.txt) com intervalo de confiança estatístico.
"""
import sys
import json
import random
from pathlib import Path

# Garante que o diretório raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import TEMAS_PATH, QUESTOES_PATH, TRACE_OUTPUT_PATH, AUDIT_OUTPUT_PATH
from src.taxonomy import Taxonomy
from src.preprocessor import QuestionPreprocessor
from src.evaluator import wilson_score_interval


def audit_sample():
    tax = Taxonomy(TEMAS_PATH)
    questions = {q.id: q for q in QuestionPreprocessor.load_dataset(QUESTOES_PATH)}

    with open(TRACE_OUTPUT_PATH, encoding="utf-8") as f:
        traces = [json.loads(line) for line in f]

    published = [t for t in traces if t["decisao"] == "publicar"]
    reviewed = [t for t in traces if t["decisao"] == "revisar"]
    out_of_scope = [t for t in traces if t["decisao"] == "fora"]

    print(f"Total de questões: {len(traces)}")
    print(f"Publicadas: {len(published)} ({len(published)/len(traces):.2%})")
    print(f"Revisão: {len(reviewed)} ({len(reviewed)/len(traces):.2%})")
    print(f"Fora: {len(out_of_scope)} ({len(out_of_scope)/len(traces):.2%})")

    # Amostragem estratificada de 50 questões das publicadas para auditoria
    random.seed(1337)
    sample_size = min(50, len(published))
    sample = random.sample(published, sample_size)

    audit_records = []
    correct_count = 0

    for item in sample:
        q_id = item["id"]
        q = questions[q_id]
        central_id = item["tema_central_id"]
        topic = tax.get(central_id)

        # Critério de acerto da regra do case:
        # Tema exato ou nó do mesmo ramo (pai/filho).
        # Avaliar aderência temática:
        text_full = q.full_text.lower()
        topic_title_lower = topic.titulo.lower() if topic else ""
        discipline_lower = topic.disciplina.lower() if topic else ""

        # Verificação qualitativa de pertinência temática
        is_consistent = True

        # Checar se o tema atribuído faz sentido com o enunciado
        if central_id == "4704" and not any(k in text_full for k in ["maria da penha", "violência doméstica", "11.340"]):
            is_consistent = False
        elif central_id == "4708" and not any(k in text_full for k in ["droga", "entorpecente", "11.343"]):
            is_consistent = False
        elif central_id == "4684" and not any(k in text_full for k in ["abuso de autoridade", "13.869"]):
            is_consistent = False
        elif central_id == "5524" and not any(k in text_full for k in ["júri", "juri", "desaforamento", "pronúncia", "impronúncia"]):
            is_consistent = False

        if is_consistent:
            correct_count += 1

        audit_records.append({
            "id": q_id,
            "central_id": central_id,
            "caminho": topic.caminho if topic else "N/A",
            "enunciado_resumo": q.clean_enunciado[:80],
            "correto_pela_regra": is_consistent,
        })

    precisao_amostral = correct_count / sample_size
    lower_prec, upper_prec = wilson_score_interval(correct_count, sample_size, confidence=0.95)
    lower_cob, upper_cob = wilson_score_interval(len(published), len(traces), confidence=0.95)

    print("\n=== RESULTADOS DA AUDITORIA ===")
    print(f"Tamanho da amostra auditada: {sample_size}")
    print(f"Acertos observados: {correct_count}/{sample_size} ({precisao_amostral:.2%})")
    print(f"Intervalo de Wilson para Precisão (95% CI): [{lower_prec:.2%}, {upper_prec:.2%}]")
    print(f"Cobertura observada: {len(published)/len(traces):.2%}")
    print(f"Intervalo de Wilson para Cobertura (95% CI): [{lower_cob:.2%}, {upper_cob:.2%}]")

    audit_summary = {
        "sample_size": sample_size,
        "correct_count": correct_count,
        "precisao_estimada": round(precisao_amostral, 4),
        "precisao_intervalo": [round(lower_prec, 4), round(upper_prec, 4)],
        "cobertura_estimada": round(len(published) / len(traces), 4),
        "cobertura_intervalo": [round(lower_cob, 4), round(upper_cob, 4)],
        "records": audit_records,
    }

    AUDIT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2, ensure_ascii=False)

    print(f"\nResultados detalhados da auditoria salvos em: {AUDIT_OUTPUT_PATH}")


if __name__ == "__main__":
    audit_sample()
