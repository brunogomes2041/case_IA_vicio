"""Taxonomy Tree and Navigation for Legal Questions Classification.

Handles ingestion of temas.csv, tree relations (parent, children, ancestors,
descendants, siblings), validation of active/inactive nodes, and evaluation
logic (same-branch rule: parent/child relations count as correct).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class TopicNode:
    tema_id: str
    parent_id: str
    disciplina: str
    nivel: int
    titulo: str
    caminho: str
    descricao: str
    status: str  # 'active' or 'inactive'
    children: List[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def is_root(self) -> bool:
        return self.nivel == 0

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0


class TaxonomyTree:
    """Manages hierarchical relations between legal topics."""

    # Explicit canonical mapping of fragmented 67xx pseudo-nodes to canonical nodes
    CANONICAL_MAPPINGS: Dict[str, str] = {
        "6716": "4684",  # Penal > Abuso de Autoridade -> Leg. Especial > Abuso de Autoridade
        "6717": "4688",  # Penal > Crimes contra o meio ambiente -> Leg. Especial > Crimes contra o meio ambiente
        "6718": "5087",  # Penal > Crimes Contra a Adm Pública (Parte 1) -> Penal > Crimes Contra a Adm Pública
        "6719": "5087",  # Penal > Crimes Contra a Adm Pública (Parte 2) -> Penal > Crimes Contra a Adm Pública
        "6720": "5157",  # Penal > Crimes Contra o Patrimônio (Parte 1) -> Penal > Crimes Contra o Patrimônio
        "6721": "5157",  # Penal > Crimes Contra o Patrimônio (Parte 2) -> Penal > Crimes Contra o Patrimônio
        "6722": "4696",  # Penal > Estatuto do Idoso - Crimes -> Leg. Especial > Estaturo de Idoso - Crimes
        "6723": "4702",  # Penal > Lavagem de Dinheiro -> Leg. Especial > Lavagem de Dinheiro
        "6724": "4704",  # Penal > Lei Maria da Penha -> Leg. Especial > Lei Maria da Penha
        "6725": "4705",  # Penal > Organizações Criminosas -> Leg. Especial > Organizações Criminosas
        "6726": "5199",  # Penal > Teoria da Pena (Parte 1) -> Penal > Teoria da Pena
        "6727": "5199",  # Penal > Teoria da Pena (Parte 2) -> Penal > Teoria da Pena
        "6728": "4708",  # Penal > Tráfico de Drogas -> Leg. Especial > Tráfico de Drogas
        "6732": "5480",  # Processo Penal > Competência (Parte 1) -> Processo Penal > Competência
        "6733": "5480",  # Processo Penal > Competência (Parte 2) -> Processo Penal > Competência
        "6734": "4703",  # Processo Penal > Lei de Execução Penal -> Leg. Especial > Lei de Execução Penal
        "6735": "5543",  # Processo Penal > Provas em Espécie -> Processo Penal > Provas em Espécies
        "6736": "5560",  # Processo Penal > Recursos (Parte 03) -> Processo Penal > Recursos em Espécies
        "6737": "5572",  # Processo Penal > Sentença Penal (Parte 1) -> Processo Penal > Sentença Penal
        "6738": "5572",  # Processo Penal > Sentença Penal (Parte 2) -> Processo Penal > Sentença Penal
    }

    def __init__(self, temas_path: str | Path | None = None):
        self.nodes: Dict[str, TopicNode] = {}
        if temas_path is None:
            for candidate in ["data/temas.csv", "anexos-case-ia/anexos/temas.csv", "../data/temas.csv"]:
                if Path(candidate).exists():
                    temas_path = candidate
                    break
        if temas_path is None:
            temas_path = "data/temas.csv"
        self.load(temas_path)

    def load(self, temas_path: str | Path) -> None:
        path = Path(temas_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de temas não encontrado: {path}")

        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                node = TopicNode(
                    tema_id=row["tema_id"].strip(),
                    parent_id=row["parent_id"].strip(),
                    disciplina=row["disciplina"].strip(),
                    nivel=int(row["nivel"].strip()),
                    titulo=row["titulo"].strip(),
                    caminho=row["caminho"].strip(),
                    descricao=row["descricao"].strip(),
                    status=row["status"].strip(),
                )
                self.nodes[node.tema_id] = node

        # Build children lists
        for node in self.nodes.values():
            if node.parent_id and node.parent_id in self.nodes:
                self.nodes[node.parent_id].children.append(node.tema_id)

    def get(self, tema_id: str) -> Optional[TopicNode]:
        return self.nodes.get(tema_id)

    def is_active(self, tema_id: str) -> bool:
        node = self.get(tema_id)
        return node is not None and node.is_active

    def get_ancestors(self, tema_id: str) -> List[TopicNode]:
        """Returns ancestors ordered from immediate parent up to root."""
        ancestors: List[TopicNode] = []
        curr = self.get(tema_id)
        while curr and curr.parent_id:
            parent = self.get(curr.parent_id)
            if parent:
                ancestors.append(parent)
                curr = parent
            else:
                break
        return ancestors

    def get_ancestor_ids(self, tema_id: str) -> Set[str]:
        return {a.tema_id for a in self.get_ancestors(tema_id)}

    def get_descendants(self, tema_id: str) -> List[TopicNode]:
        """Returns all descendants in breadth-first order."""
        descendants: List[TopicNode] = []
        node = self.get(tema_id)
        if not node:
            return descendants

        queue = list(node.children)
        while queue:
            child_id = queue.pop(0)
            child = self.get(child_id)
            if child:
                descendants.append(child)
                queue.extend(child.children)
        return descendants

    def get_descendant_ids(self, tema_id: str) -> Set[str]:
        return {d.tema_id for d in self.get_descendants(tema_id)}

    def get_parent(self, tema_id: str) -> Optional[TopicNode]:
        node = self.get(tema_id)
        if node and node.parent_id:
            return self.get(node.parent_id)
        return None

    def get_siblings(self, tema_id: str) -> List[TopicNode]:
        node = self.get(tema_id)
        if not node or not node.parent_id:
            return []
        parent = self.get(node.parent_id)
        if not parent:
            return []
        return [self.get(cid) for cid in parent.children if cid != tema_id and self.get(cid)]

    def is_same_branch(self, pred_id: str, true_id: str) -> bool:
        """Evaluates whether predicted topic is counted as correct under case rules.

        Rules from Case PDF:
        - Exact match is correct.
        - Node in same branch (parent or child) is correct:
          'Conta como certo publicar no tema que a equipe atribuiu à questão,
          ou num nó do mesmo ramo (pai ou filho dele), porque o aluno que estuda
          um tema também vê as questões dos subtemas. Publicar em outro subtema
          do mesmo tema conta como erro.'
        """
        if not pred_id or not true_id:
            return False
        if pred_id == true_id:
            return True

        # Check if pred_id is ancestor of true_id (e.g. parent)
        if pred_id in self.get_ancestor_ids(true_id):
            return True

        # Check if pred_id is descendant of true_id (e.g. child)
        if pred_id in self.get_descendant_ids(true_id):
            return True

        # If true_id or pred_id maps canonically to one another
        canon_pred = self.CANONICAL_MAPPINGS.get(pred_id, pred_id)
        canon_true = self.CANONICAL_MAPPINGS.get(true_id, true_id)
        if canon_pred == canon_true:
            return True
        if canon_pred in self.get_ancestor_ids(canon_true) or canon_pred in self.get_descendant_ids(canon_true):
            return True

        return False

    def get_canonical_id(self, tema_id: str) -> str:
        """Returns canonical ID if tema_id is a known fragmented pseudo-topic."""
        return self.CANONICAL_MAPPINGS.get(tema_id, tema_id)

    def get_active_topics(self) -> List[TopicNode]:
        return [t for t in self.nodes.values() if t.is_active]

    def get_leaf_active_topics(self) -> List[TopicNode]:
        return [t for t in self.nodes.values() if t.is_active and t.is_leaf]

    # Alias
    get_all_active = get_active_topics


# Aliases para compatibilidade
Taxonomy = TaxonomyTree
Topic = TopicNode
