"""
Módulo de avaliação, validação estatística e geração dos entregáveis.
Calcula intervalos de confiança de Wilson, gera previsao.txt e exporta publicacao.csv.
"""
import csv
import math
from pathlib import Path
from typing import List, Dict, Tuple, Any
from src.decision_engine import ClassificationResult


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calcula intervalo de confiança de Wilson para uma proporção binomial."""
    if total == 0:
        return 0.0, 0.0

    # z para 95% = 1.95996
    z = 1.959964 if confidence == 0.95 else 1.644853  # 90%
    p = successes / total
    denominator = 1.0 + (z**2) / total
    center = (p + (z**2) / (2.0 * total)) / denominator
    margin = (z * math.sqrt((p * (1.0 - p) + (z**2) / (4.0 * total)) / total)) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return lower, upper


class Evaluator:
    @staticmethod
    def validate_results(results: List[ClassificationResult]) -> List[str]:
        """Valida conformidade das predições com o dicionário de campos do LEIA-ME.md."""
        errors = []
        valid_decisions = {"publicar", "revisar", "fora"}

        for r in results:
            if r.decisao not in valid_decisions:
                errors.append(f"Questão {r.id}: decisão inválida '{r.decisao}'")
            if r.decisao in {"publicar", "revisar"} and not r.tema_central_id:
                errors.append(f"Questão {r.id}: tema_central_id obrigatório em '{r.decisao}'")
            if r.decisao == "fora" and r.tema_central_id:
                errors.append(f"Questão {r.id}: tema_central_id deve ser vazio em 'fora'")
            if r.decisao in {"revisar", "fora"} and not r.motivo:
                errors.append(f"Questão {r.id}: motivo obrigatório em '{r.decisao}'")
            if not (0.0 <= r.confianca <= 1.0):
                errors.append(f"Questão {r.id}: confiança fora do intervalo [0, 1]: {r.confianca}")

        return errors

    @staticmethod
    def export_publicacao_csv(results: List[ClassificationResult], output_path: Path) -> None:
        """Exporta o arquivo publicacao.csv exatamente no padrão exigido."""
        fieldnames = ["id", "decisao", "tema_central_id", "extras_ids", "confianca", "motivo"]
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "id": r.id,
                    "decisao": r.decisao,
                    "tema_central_id": r.tema_central_id,
                    "extras_ids": r.extras_ids,
                    "confianca": f"{r.confianca:.2f}",
                    "motivo": r.motivo,
                })

    @staticmethod
    def generate_previsao_txt(
        precisao_prevista: float,
        precisao_intervalo: Tuple[float, float],
        cobertura_prevista: float,
        cobertura_intervalo: Tuple[float, float],
        explicacao_texto: str,
        output_path: Path,
    ) -> None:
        """Gera previsao.txt com cabeçalho estrito e justificativa textual."""
        content = (
            f"precisao_prevista: {precisao_prevista:.2f}\n"
            f"precisao_intervalo: {precisao_intervalo[0]:.2f}-{precisao_intervalo[1]:.2f}\n"
            f"cobertura_prevista: {cobertura_prevista:.2f}\n"
            f"cobertura_intervalo: {cobertura_intervalo[0]:.2f}-{cobertura_intervalo[1]:.2f}\n\n"
            f"{explicacao_texto.strip()}\n"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
