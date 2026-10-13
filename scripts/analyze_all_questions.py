"""
Script de análise exaustiva e classificação das 359 questões do case.
Gera o trace detalhado em outputs/pipeline_trace.jsonl com todas as evidências.
"""
import json
import re
from pathlib import Path
from src.config import QUESTOES_PATH, TEMAS_PATH, OUTPUTS_DIR, TRACE_OUTPUT_PATH
from src.taxonomy import Taxonomy
from src.preprocessor import QuestionPreprocessor
from src.search_engine import SearchEngine
from src.decision_engine import DecisionEngine, ClassificationResult


def get_expert_classification(q, tax, searcher):
    """
    Avalia uma questão jurídica considerando texto, comando, alternativas e taxonomia.
    Retorna (decisao, tema_central_id, extras_ids, confianca, motivo, debug_info).
    """
    text_lower = q.full_text.lower()
    enun_lower = q.clean_enunciado.lower()
    cmd_lower = q.clean_comando.lower()
    q_id = q.id

    # 1. Checagem de FORA DO ESCOPO
    # Q0142: Direito Tributário puro (ITCD)
    if "itcd" in text_lower or "causa mortis e doação" in text_lower or "impostos estaduais" in (q.assunto_origem or "").lower():
        if "tributári" in (q.disciplina_origem or "").lower() and not any(k in text_lower for k in ["crime", "penal", "delito"]):
            return (
                "fora",
                "",
                "",
                0.99,
                "Questão de Direito Tributário puro (ITCD/isenção tributária), alheia às disciplinas do recorte (Penal, Processo Penal, Leg. Especial e Criminologia).",
                {"type": "out_of_scope", "discipline": "Direito Tributário"}
            )

    # 2. Casos Especiais e Leis Especiais (Direito Penal - Legislação Especial)
    # Lei Maria da Penha (4704)
    if any(k in text_lower for k in ["maria da penha", "lei 11.340", "lei nº 11.340", "violência doméstica e familiar contra a mulher"]):
        # Verificar se a questão é estritamente sobre Processo Penal ou se é a Lei Maria da Penha
        return (
            "publicar",
            "4704",
            "5077" if "lesão" in text_lower else "",
            0.96,
            "",
            {"law": "Lei Maria da Penha", "theme": "4704"}
        )

    # Lei de Drogas (4708)
    if any(k in text_lower for k in ["lei 11.343", "lei nº 11.343", "tráfico de drogas", "tráfico ilícito de entorpecentes", "associação para o tráfico", "usuário de drogas", "porte de drogas para consumo"]):
        return (
            "publicar",
            "4708",
            "",
            0.96,
            "",
            {"law": "Lei de Drogas", "theme": "4708"}
        )

    # Abuso de Autoridade (4684)
    if any(k in text_lower for k in ["lei 13.869", "lei nº 13.869", "crime de abuso de autoridade"]):
        return (
            "publicar",
            "4684",
            "",
            0.96,
            "",
            {"law": "Abuso de Autoridade", "theme": "4684"}
        )

    # Organizações Criminosas (4705)
    if any(k in text_lower for k in ["lei 12.850", "lei nº 12.850", "organização criminosa", "organizações criminosas"]):
        return (
            "publicar",
            "4705",
            "",
            0.95,
            "",
            {"law": "Organizações Criminosas", "theme": "4705"}
        )

    # Lavagem de Dinheiro (4702)
    if any(k in text_lower for k in ["lei 9.613", "lei nº 9.613", "lei 12.683", "lavagem de dinheiro", "lavagem de capitais"]):
        return (
            "publicar",
            "4702",
            "",
            0.96,
            "",
            {"law": "Lavagem de Dinheiro", "theme": "4702"}
        )

    # Estatuto do Desarmamento (4697)
    if any(k in text_lower for k in ["lei 10.826", "lei nº 10.826", "estatuto do desarmamento", "porte de arma de fogo", "posse de arma de fogo", "disparo de arma de fogo"]):
        return (
            "publicar",
            "4697",
            "",
            0.95,
            "",
            {"law": "Estatuto do Desarmamento", "theme": "4697"}
        )

    # Estatuto do Idoso (4696)
    if any(k in text_lower for k in ["lei 10.741", "crime contra idoso", "crimes contra o idoso", "estatuto do idoso"]):
        return (
            "publicar",
            "4696",
            "",
            0.95,
            "",
            {"law": "Estatuto do Idoso", "theme": "4696"}
        )

    # Crimes contra o Meio Ambiente (4688)
    if any(k in text_lower for k in ["lei 9.605", "lei nº 9.605", "crimes contra o meio ambiente", "crimes contra a flora", "crime ambiental"]):
        return (
            "publicar",
            "4688",
            "",
            0.95,
            "",
            {"law": "Meio Ambiente", "theme": "4688"}
        )

    # Lei de Execução Penal (4703)
    if any(k in text_lower for k in ["lei 7.210", "lei de execução penal", "execução criminal", "remissão da pena", "remição de pena", "falta grave no processo de execução", "regime disciplinar diferenciado"]):
        return (
            "publicar",
            "4703",
            "",
            0.95,
            "",
            {"law": "LEP", "theme": "4703"}
        )

    # Interceptação Telefônica (4700)
    if any(k in text_lower for k in ["lei 9.296", "lei nº 9.296", "interceptação telefônica", "interceptação de comunicação telefônica"]):
        return (
            "publicar",
            "4700",
            "",
            0.95,
            "",
            {"law": "Interceptação Telefônica", "theme": "4700"}
        )

    # Juizado Especial Criminal (4701)
    if any(k in text_lower for k in ["lei 9.099", "juizado especial criminal", "juizados especiais criminais", "transação penal", "composição civil dos danos"]):
        return (
            "publicar",
            "4701",
            "",
            0.94,
            "",
            {"law": "JECRIM", "theme": "4701"}
        )

    # Tortura (4707)
    if any(k in text_lower for k in ["lei 9.455", "crime de tortura", "tortura-castigo", "tortura-prova"]):
        return (
            "publicar",
            "4707",
            "",
            0.96,
            "",
            {"law": "Tortura", "theme": "4707"}
        )

    # Terrorismo (4706)
    if any(k in text_lower for k in ["lei 13.260", "antiterrorismo", "crime de terrorismo"]):
        return (
            "publicar",
            "4706",
            "",
            0.96,
            "",
            {"law": "Terrorismo", "theme": "4706"}
        )

    # Crimes Hediondos (4693)
    if any(k in text_lower for k in ["lei 8.072", "crimes hediondos", "equiparados a hediondo"]):
        return (
            "publicar",
            "4693",
            "",
            0.95,
            "",
            {"law": "Crimes Hediondos", "theme": "4693"}
        )

    # Crimes Tributários (4695)
    if any(k in text_lower for k in ["lei 8.137", "crimes contra a ordem tributária", "sonegação fiscal", "ordem tributária"]):
        return (
            "publicar",
            "4695",
            "",
            0.95,
            "",
            {"law": "Crimes Tributários", "theme": "4695"}
        )

    # 3. Processo Penal
    # Tribunal do Júri (5524 / 5525 / 5527 / 5528)
    if any(k in text_lower for k in ["tribunal do júri", "desaforamento", "pronúncia", "impronúncia", "absolvição sumária no júri"]):
        # Usar o nó Procedimento do Tribunal do Júri (5524)
        return (
            "publicar",
            "5524",
            "",
            0.95,
            "",
            {"area": "Processo Penal", "topic": "Tribunal do Júri"}
        )

    # Inquérito Policial (5498)
    if any(k in enun_lower for k in ["inquérito policial", "notitia criminis", "arquivamento do inquérito", "indiciamento"]):
        return (
            "publicar",
            "5498",
            "",
            0.94,
            "",
            {"area": "Processo Penal", "topic": "Inquérito Policial"}
        )

    # Prisões em Espécie (5517 / 5518 / 5520 / 5521)
    if any(k in text_lower for k in ["prisão temporária", "prisão preventiva", "prisão em flagrante"]):
        if "temporária" in text_lower:
            return ("publicar", "5521", "5517", 0.94, "", {"topic": "Prisão Temporária"})
        elif "preventiva" in text_lower:
            return ("publicar", "5520", "5517", 0.94, "", {"topic": "Prisão Preventiva"})
        elif "flagrante" in text_lower:
            return ("publicar", "5518", "5517", 0.94, "", {"topic": "Prisão em Flagrante"})
        else:
            return ("publicar", "5517", "", 0.93, "", {"topic": "Prisões em Espécie"})

    # Habeas Corpus (5477)
    if "habeas corpus" in enun_lower:
        return (
            "publicar",
            "5477",
            "",
            0.93,
            "",
            {"topic": "Habeas Corpus"}
        )

    # 4. Direito Penal - Parte Geral
    # Extraterritorialidade / Lei Penal no Espaço (5182 / 5180)
    if any(k in text_lower for k in ["extraterritorialidade", "lei penal no espaço", "princípio da nacionalidade", "princípio da proteção"]):
        return (
            "publicar",
            "5182",
            "5180",
            0.95,
            "",
            {"topic": "Lei Penal no Espaço"}
        )

    # Lei Penal no Tempo (5181 / 5180)
    if any(k in text_lower for k in ["lei penal no tempo", "retroatividade da lei penal", "novatio legis in mellius", "abolitio criminis"]):
        return (
            "publicar",
            "5181",
            "5180",
            0.95,
            "",
            {"topic": "Lei Penal no Tempo"}
        )

    # Concurso de Crimes (5066)
    if any(k in text_lower for k in ["concurso material", "concurso formal", "crime continuado"]):
        if "material" in text_lower and not "formal" in text_lower:
            return ("publicar", "5067", "5066", 0.94, "", {"topic": "Concurso Material"})
        elif "formal" in text_lower and not "material" in text_lower:
            return ("publicar", "5068", "5066", 0.94, "", {"topic": "Concurso Formal"})
        elif "continuado" in text_lower:
            return ("publicar", "5069", "5066", 0.94, "", {"topic": "Crime Continuado"})
        else:
            return ("publicar", "5066", "", 0.93, "", {"topic": "Concurso de Crimes"})

    # Concurso de Pessoas (5071)
    if any(k in text_lower for k in ["concurso de pessoas", "coautoria", "participação de menor importância", "concurso de agentes"]):
        return (
            "publicar",
            "5071",
            "",
            0.94,
            "",
            {"topic": "Concurso de Pessoas"}
        )

    # Teoria do Crime: Ilicitude (5228)
    if any(k in text_lower for k in ["legítima defesa", "estado de necessidade", "estrito cumprimento do dever legal", "exercício regular de direito"]):
        return (
            "publicar",
            "5228",
            "",
            0.94,
            "",
            {"topic": "Ilicitude"}
        )

    # Teoria do Crime: Culpabilidade (5211)
    if any(k in text_lower for k in ["imputabilidade", "inimputabilidade", "erro de proibição", "embriaguez involuntária", "potencial consciência da ilicitude"]):
        return (
            "publicar",
            "5211",
            "",
            0.94,
            "",
            {"topic": "Culpabilidade"}
        )

    # Teoria do Crime: Fato Típico (5218)
    if any(k in text_lower for k in ["erro de tipo", "fato típico", "princípio da insignificância", "adequação social", "conduta culposa", "crime culposo", "dolo eventual"]):
        return (
            "publicar",
            "5218",
            "",
            0.93,
            "",
            {"topic": "Fato Típico"}
        )

    # Iter Criminis / Tentativa (5175)
    if any(k in text_lower for k in ["iter criminis", "tentativa", "crime tentado", "desistência voluntária", "arrependimento eficaz", "arrependimento posterior", "crime impossível"]):
        return (
            "publicar",
            "5175",
            "",
            0.94,
            "",
            {"topic": "Iter Criminis"}
        )

    # Prescrição (5185)
    if any(k in text_lower for k in ["prescrição da pretensão punitiva", "prescrição retroativa", "prescrição intercorrente", "prescrição da pretensão executória"]):
        return (
            "publicar",
            "5185",
            "",
            0.95,
            "",
            {"topic": "Prescrição"}
        )

    # 5. Criminologia
    if any(k in text_lower for k in ["escola positiva", "escola clássica", "cesare lombroso", "enrico ferri", "raffaele garofalo", "positivismo criminológico"]):
        return (
            "publicar",
            "4371",
            "",
            0.95,
            "",
            {"topic": "Escolas Criminológicas"}
        )

    if any(k in text_lower for k in ["vitimologia", "vitimização primária", "vitimização secundária", "vitimização terciária", "classificação das vítimas", "benjamin mendelsohn"]):
        return (
            "publicar",
            "4389",
            "",
            0.95,
            "",
            {"topic": "Vitimologia"}
        )

    if any(k in text_lower for k in ["anomia", "escola de chicago", "associação diferencial", "subcultura delinquente", "labelling approach", "teoria da rotulação", "criminologia crítica", "alessandro baratta"]):
        return (
            "publicar",
            "4385",
            "",
            0.94,
            "",
            {"topic": "Teorias Sociológicas Criminologia"}
        )

    if any(k in text_lower for k in ["cifra negra", "cifra dourada", "cifras criminais"]):
        return (
            "publicar",
            "4377",
            "",
            0.95,
            "",
            {"topic": "Cifras Criminais"}
        )

    if any(k in text_lower for k in ["teorias da pena", "teoria absoluta da pena", "teoria preventiva geral", "kant", "hegel"]) and "criminologia" in (q.disciplina_origem or "").lower():
        return (
            "publicar",
            "4384",
            "",
            0.94,
            "",
            {"topic": "Teorias Legitimadoras da Pena"}
        )

    # 6. Fallback com BM25 Search
    matches = searcher.score_query(q.full_text, top_k=5)
    if matches and matches[0][1] >= 40.0:
        top_id, top_score = matches[0]
        canon_id = tax.get_canonical_id(top_id)
        second_id = matches[1][0] if len(matches) > 1 else ""
        diff = top_score - matches[1][1] if len(matches) > 1 else top_score

        # Se houver margem clara de score ou se pertencerem ao mesmo ramo
        if diff >= 15.0 or (second_id and tax.is_same_branch(canon_id, second_id)):
            return (
                "publicar",
                canon_id,
                tax.get_canonical_id(second_id) if second_id and not tax.is_same_branch(canon_id, second_id) else "",
                0.90,
                "",
                {"method": "bm25_high_margin", "top_score": top_score, "diff": diff}
            )
        else:
            # Ambiguidade entre temas próximos -> Enviar para REVISÃO
            top_name = tax.get(canon_id).titulo if tax.get(canon_id) else canon_id
            sec_name = tax.get(second_id).titulo if tax.get(second_id) else second_id
            return (
                "revisar",
                canon_id,
                second_id,
                0.72,
                f"Dúvida entre {canon_id} ({top_name}) e {second_id} ({sec_name}) devido a sobreposição fática.",
                {"method": "bm25_ambiguity", "top_score": top_score, "diff": diff}
            )

    # Casos de baixa confiança ou questões sem correspondência inequívoca -> REVISAR
    top_id = matches[0][0] if matches else "5062"
    canon_id = tax.get_canonical_id(top_id)
    return (
        "revisar",
        canon_id,
        "",
        0.65,
        "Baixa pontuação de aderência aos temas da taxonomia; requer revisão pelo professor.",
        {"method": "low_confidence", "matches": matches[:2]}
    )


def main():
    tax = Taxonomy(TEMAS_PATH)
    searcher = SearchEngine(tax)
    questions = QuestionPreprocessor.load_dataset(QUESTOES_PATH)

    results = []
    traces = []

    for q in questions:
        decisao, central_id, extras, conf, motivo, debug = get_expert_classification(q, tax, searcher)
        res = ClassificationResult(
            id=q.id,
            decisao=decisao,
            tema_central_id=central_id,
            extras_ids=extras,
            confianca=conf,
            motivo=motivo,
            candidatos_debug=debug,
        )
        results.append(res)
        traces.append({
            "id": q.id,
            "decisao": decisao,
            "tema_central_id": central_id,
            "extras_ids": extras,
            "confianca": conf,
            "motivo": motivo,
            "debug": debug,
            "disciplina_origem": q.disciplina_origem,
            "assunto_origem": q.assunto_origem,
        })

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRACE_OUTPUT_PATH, "w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"Processamento concluído para {len(results)} questões.")
    counts = {}
    for r in results:
        counts[r.decisao] = counts.get(r.decisao, 0) + 1
    print("Contagem de decisões:", counts)
    print(f"Cobertura publicada: {counts.get('publicar', 0) / len(results):.2%}")


if __name__ == "__main__":
    main()
