"""
Motor de busca e ranqueamento semântico de tópicos jurídicos.
Implementa BM25 puro em Python com boosting de termos canônicos e frases exatas.
"""
import re
import math
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Any
from src.taxonomy import Taxonomy, Topic


# Stopwords comuns em português e termos genéricos de concurso que não agregam valor taxonômico
STOPWORDS = {
    "a", "ao", "aos", "aquela", "aquelas", "aquele", "aqueles", "aquilo", "as", "até",
    "com", "como", "da", "das", "de", "dela", "delas", "dele", "deles", "depois",
    "do", "dos", "e", "é", "ela", "elas", "ele", "eles", "em", "entre", "era", "eram",
    "éramos", "essa", "essas", "esse", "esses", "esta", "estas", "este", "estes", "eu",
    "foi", "fomos", "foram", "isso", "isto", "já", "lhe", "lhes", "mais", "mas", "me",
    "mesmo", "meu", "meus", "minha", "minhas", "muito", "na", "não", "nas", "nem",
    "no", "nos", "nós", "nossa", "nossas", "nosso", "nossos", "num", "numa", "o", "os",
    "ou", "para", "pela", "pelas", "pelo", "pelos", "por", "qual", "quando", "que",
    "quem", "se", "seja", "sejamos", "sejam", "sem", "será", "serão", "seu", "seus",
    "só", "somos", "sou", "sua", "suas", "também", "te", "tem", "temos", "tenho",
    "terá", "terão", "teu", "teus", "teve", "ti", "tido", "tinha", "tinham", "toda",
    "todas", "todo", "todos", "tu", "tua", "tuas", "um", "uma", "você", "vocês",
    # Termos de concurso genéricos
    "assinale", "alternativa", "correta", "incorreta", "abaixo", "assertiva", "assertivas",
    "opção", "considere", "caso", "hipotética", "situação", "acerca", "diante",
    "analise", "itens", "seguintes", "seguinte", "afirmativa", "afirmativas",
}


def tokenize(text: str) -> List[str]:
    """Tokeniza texto em palavras minúsculas sem pontuação."""
    tokens = re.findall(r"[a-zá-ú0-9]+", (text or "").lower())
    return [t for t in tokens if len(t) > 2 and t not in STOPWORDS]


class SearchEngine:
    def __init__(self, taxonomy: Taxonomy, k1: float = 1.5, b: float = 0.75):
        self.taxonomy = taxonomy
        self.k1 = k1
        self.b = b
        self.topics: List[Topic] = taxonomy.get_all_active()
        self.num_docs = len(self.topics)
        self.doc_lengths: Dict[str, int] = {}
        self.doc_tokens: Dict[str, List[str]] = {}
        self.inverted_index: Dict[str, List[str]] = defaultdict(list)
        self.term_freqs: Dict[str, Counter] = {}
        self.idf: Dict[str, float] = {}

        self._build_index()

    def _build_index(self):
        total_len = 0
        df = Counter()

        for t in self.topics:
            # Pesar o título mais vezes no documento do tópico para refletir importância
            doc_text = f"{t.titulo} {t.titulo} {t.titulo} {t.caminho} {t.caminho} {t.descricao}"
            tokens = tokenize(doc_text)
            self.doc_tokens[t.tema_id] = tokens
            self.doc_lengths[t.tema_id] = len(tokens)
            total_len += len(tokens)

            tf = Counter(tokens)
            self.term_freqs[t.tema_id] = tf

            for term in tf.keys():
                self.inverted_index[term].append(t.tema_id)
                df[term] += 1

        self.avg_dl = (total_len / self.num_docs) if self.num_docs > 0 else 1.0

        for term, freq in df.items():
            # BM25 IDF com suavização
            self.idf[term] = math.log(1.0 + (self.num_docs - freq + 0.5) / (freq + 0.5))

    def score_query(self, query_text: str, top_k: int = 10, discipline_filter: str = None) -> List[Tuple[str, float]]:
        """
        Retorna os top_k tópicos com seus respectivos scores BM25 + bônus de frase exata.
        """
        q_tokens = tokenize(query_text)
        if not q_tokens:
            return []

        query_text_lower = query_text.lower()
        scores = defaultdict(float)

        # 1. BM25 scoring
        for term in q_tokens:
            if term not in self.idf:
                continue
            term_idf = self.idf[term]
            posting_list = self.inverted_index[term]

            for doc_id in posting_list:
                tf = self.term_freqs[doc_id][term]
                doc_len = self.doc_lengths[doc_id]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_dl))
                scores[doc_id] += term_idf * (numerator / denominator)

        # 2. Bônus de correspondência de frase exata no título ou caminho
        for doc_id in list(scores.keys()):
            topic = self.taxonomy.get(doc_id)
            if not topic:
                continue

            # Filtro opcional por disciplina
            if discipline_filter and topic.disciplina != discipline_filter:
                scores[doc_id] *= 0.1

            titulo_lower = topic.titulo.lower()
            if len(titulo_lower) > 3 and titulo_lower in query_text_lower:
                # Frase inteira do título está no enunciado/comando
                scores[doc_id] += 8.0

        # Ordenar e filtrar
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
