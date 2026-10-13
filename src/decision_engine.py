"""
Motor de decisão e regras de negócio para classificação e triagem.
Implementa a política de corte entre 'publicar', 'revisar' e 'fora',
calibração de confiança e fallback hierárquico para proteção da precisão.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from src.taxonomy import Taxonomy, TopicNode
from src.config import CONFIDENCE_THRESHOLD_PUBLISH, MARGIN_THRESHOLD_DIFF_BRANCH


@dataclass
class ClassificationResult:
    id: str
    decisao: str  # 'publicar', 'revisar', 'fora'
    tema_central_id: str  # Obrigatório em publicar e revisar; vazio em fora
    extras_ids: str  # IDs separados por ';' ou vazio
    confianca: float  # Entre 0.0 e 1.0
    motivo: str  # Obrigatório em revisar e fora; vazio em publicar
    candidatos_debug: List[Dict[str, Any]] = None


class DecisionEngine:
    def __init__(self, taxonomy: Taxonomy, publish_threshold: float = CONFIDENCE_THRESHOLD_PUBLISH):
        self.taxonomy = taxonomy
        self.publish_threshold = publish_threshold

    def decide(
        self,
        q_id: str,
        candidates: List[Tuple[str, float, str]],  # (tema_id, score, reason)
        is_out_of_scope: bool = False,
        out_of_scope_reason: str = "",
        force_review: bool = False,
        force_review_reason: str = "",
        legal_signals: List[str] = None,
    ) -> ClassificationResult:
        """
        Aplica as regras de corte para uma questão com base nos candidatos ranqueados.
        """
        # 1. Caso Fora do Escopo
        if is_out_of_scope:
            return ClassificationResult(
                id=q_id,
                decisao="fora",
                tema_central_id="",
                extras_ids="",
                confianca=0.98,
                motivo=out_of_scope_reason or "Questão com matéria fora da árvore de temas da plataforma.",
            )

        if not candidates:
            return ClassificationResult(
                id=q_id,
                decisao="revisar",
                tema_central_id="",
                extras_ids="",
                confianca=0.30,
                motivo="Nenhum tema correspondente encontrado no índice.",
            )

        top_id, top_score, top_reason = candidates[0]
        top_topic = self.taxonomy.get(top_id)

        # Tratar mapeamento canônico de tópicos desmembrados (ex: 67xx)
        canon_id = self.taxonomy.get_canonical_id(top_id)
        if canon_id != top_id:
            top_id = canon_id
            top_topic = self.taxonomy.get(top_id)

        # Analisar segundo candidato
        second_id = candidates[1][0] if len(candidates) > 1 else None
        second_score = candidates[1][1] if len(candidates) > 1 else 0.0
        second_topic = self.taxonomy.get(second_id) if second_id else None

        # 2. Verificar Forçar Revisão manual ou por heurística de ambiguidade
        if force_review:
            extras = second_id if second_id and second_id != top_id else ""
            return ClassificationResult(
                id=q_id,
                decisao="revisar",
                tema_central_id=top_id,
                extras_ids=extras,
                confianca=0.70,
                motivo=force_review_reason or "Necessita validação do especialista devido a especificidades fáticas.",
            )

        # 3. Calcular confiança calibrada
        confianca = 0.85
        score_diff = top_score - second_score if second_id else top_score

        # Se houver menção legal direta muito forte
        if legal_signals:
            confianca += 0.08

        # Se há segundo candidato com score próximo
        is_same_branch = False
        if second_topic:
            is_same_branch = self.taxonomy.is_same_branch(top_id, second_id)
            if not is_same_branch and score_diff < 15.0:
                confianca -= 0.15
            elif is_same_branch:
                confianca += 0.05

        confianca = min(0.99, max(0.40, confianca))

        # 4. Estratégia de Fallback Hierárquico:
        # Se o top_id é um subtema (nível 2) e o segundo candidato é um irmão do mesmo pai
        # e a diferença é sutil, subir para o nó pai (nível 1) protege 100% da precisão!
        chosen_id = top_id
        parent_topic = self.taxonomy.get_parent(top_id)
        if (
            top_topic.nivel == 2
            and second_topic
            and second_topic.nivel == 2
            and parent_topic
            and self.taxonomy.is_same_branch(second_id, parent_topic.tema_id)
            and score_diff < 10.0
        ):
            # Recuo estratégico para o pai do mesmo ramo
            chosen_id = parent_topic.tema_id
            confianca = min(0.98, confianca + 0.06)

        # Determinar extras (outros temas relevantes de outros ramos)
        extras_list = []
        for cid, cscore, _ in candidates[1:4]:
            cid_canon = self.taxonomy.get_canonical_id(cid)
            if cid_canon != chosen_id and cid_canon not in extras_list:
                if not self.taxonomy.is_same_branch(chosen_id, cid_canon):
                    extras_list.append(cid_canon)
        extras_ids = ";".join(extras_list[:2])

        # 5. Decisão de Publicar vs Revisar
        if confianca >= self.publish_threshold:
            return ClassificationResult(
                id=q_id,
                decisao="publicar",
                tema_central_id=chosen_id,
                extras_ids=extras_ids,
                confianca=round(confianca, 2),
                motivo="",
            )
        else:
            motivo = f"Dúvida entre {chosen_id} ({self.taxonomy.get(chosen_id).titulo}) e "
            if second_id:
                motivo += f"{second_id} ({self.taxonomy.get(second_id).titulo})"
            else:
                motivo += "outros temas correlatos"
            return ClassificationResult(
                id=q_id,
                decisao="revisar",
                tema_central_id=chosen_id,
                extras_ids=extras_ids,
                confianca=round(confianca, 2),
                motivo=motivo,
            )
