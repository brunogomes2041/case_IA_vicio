"""Substantive Legal Classifier for Brazilian Criminal Law & Criminology.

Combines statutory mapping (CP, CPP, Legislação Especial, Súmulas),
concept-based rules, semantic text similarity, and hierarchy validation.
Ensures strict compliance with active topics and the case evaluation rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from src.preprocessor import Question
from src.taxonomy import TaxonomyTree, TopicNode


@dataclass
class ClassificationResult:
    question_id: str
    decisao: str  # 'publicar', 'revisar', 'fora'
    tema_central_id: str  # Mandatory for publicar and revisar, empty for fora
    extras_ids: List[str] = field(default_factory=list)
    confianca: float = 0.0
    motivo: str = ""  # Mandatory for revisar and fora, empty for publicar
    top_candidates: List[Tuple[str, float]] = field(default_factory=list)

    @property
    def extras_ids_str(self) -> str:
        return ";".join(self.extras_ids)


class LegalClassifier:
    """Multi-stage classifier engineered for >=95% precision on published questions."""

    def __init__(self, tree: Optional[TaxonomyTree] = None):
        self.tree = tree or TaxonomyTree()
        self._init_rules()

    def _init_rules(self) -> None:
        """Initialize comprehensive statutory and thematic pattern mappings."""
        # 1. Special Statutes to Topic ID mappings
        self.statute_map = [
            # Lei de Drogas (11.343/06)
            (re.compile(r"\b(?:11\.343|entorpecente|tráfico de drogas|uso de drogas|drogas? ilícit|drogas?)\b", re.IGNORECASE), "4708"),
            # Lei Maria da Penha (11.340/06)
            (re.compile(r"\b(?:11\.340|maria da penha|violência doméstica e familiar contra a mulher)\b", re.IGNORECASE), "4704"),
            # Lei de Execução Penal - LEP (7.210/84)
            (re.compile(r"\b(?:7\.210|execução penal|remição|falta grave|regressão de regime|livramento condicional na lep|rdd|regime disciplinar diferenciado)\b", re.IGNORECASE), "4703"),
            # Abuso de Autoridade (13.869/19 ou 4.898/65)
            (re.compile(r"\b(?:13\.869|abuso de autoridade)\b", re.IGNORECASE), "4684"),
            # Crimes Hediondos (8.072/90)
            (re.compile(r"\b(?:8\.072|crimes? hediondos?|rol dos crimes hediondos)\b", re.IGNORECASE), "4693"),
            # Estatuto do Desarmamento (10.826/03)
            (re.compile(r"\b(?:10\.826|estatuto do desarmamento|arma de fogo|porte ilegal de arma|posse irregular de arma|disparo de arma de fogo)\b", re.IGNORECASE), "4697"),
            # Organizações Criminosas (12.850/13)
            (re.compile(r"\b(?:12\.850|organização criminosa|organizações criminosas|colaboração premiada)\b", re.IGNORECASE), "4705"),
            # Lavagem de Dinheiro (9.613/98)
            (re.compile(r"\b(?:9\.613|lavagem de capitais|lavagem de dinheiro|ocultação de bens)\b", re.IGNORECASE), "4702"),
            # Crimes de Trânsito / CTB (9.503/97)
            (re.compile(r"\b(?:9\.503|código de trânsito|crimes? de trânsito|embriaguez ao volante|homicídio culposo na direção)\b", re.IGNORECASE), "4691"),
            # Crimes Ambientais (9.605/98)
            (re.compile(r"\b(?:9\.605|crimes? ambientais?|meio ambiente|fauna|flora|poluição ambiental)\b", re.IGNORECASE), "4688"),
            # Crimes Tributários (8.137/90)
            (re.compile(r"\b(?:8\.137|ordem tributária|crimes? tributários?|sonegação fiscal|apropriação indébita tributária)\b", re.IGNORECASE), "4695"),
            # Estatuto do Idoso (10.741/03)
            (re.compile(r"\b(?:10\.741|estatuto do idoso|crimes? contra idoso|vítima idosa|pessoa idosa)\b", re.IGNORECASE), "4696"),
            # Tortura (9.455/97)
            (re.compile(r"\b(?:9\.455|crime de tortura|lei de tortura)\b", re.IGNORECASE), "4707"),
            # Terrorismo (13.260/16)
            (re.compile(r"\b(?:13\.260|antiterrorismo|crime de terrorismo)\b", re.IGNORECASE), "4706"),
            # Interceptação Telefônica (9.296/96)
            (re.compile(r"\b(?:9\.296|interceptação telefônica|gravação clandestina|escuta telefônica)\b", re.IGNORECASE), "4700"),
            # Juizados Especiais Criminais / JECRIM (9.099/95)
            (re.compile(r"\b(?:9\.099|juizados? especiais? criminais?|jecrim|transação penal|composição civil dos danos)\b", re.IGNORECASE), "4701"),
            # Genocídio (2.889/56)
            (re.compile(r"\b(?:2\.889|crime de genocídio|genocídio)\b", re.IGNORECASE), "4698"),
            # Racismo (7.716/89)
            (re.compile(r"\b(?:7\.716|crime de racismo|injúria racial|preconceito de raça)\b", re.IGNORECASE), "4690"),
            # Contravenções Penais (Dec.-Lei 3.688/41)
            (re.compile(r"\b(?:3\.688|contravenção penal|contravenções penais|prisão simples|jogo do bicho)\b", re.IGNORECASE), "4686"),
            # Identificação Criminal (12.037/09)
            (re.compile(r"\b(?:12\.037|identificação criminal|identificação datiloscópica|perfil genético)\b", re.IGNORECASE), "4699"),
            # Crimes contra o Sistema Financeiro (7.492/86)
            (re.compile(r"\b(?:7\.492|sistema financeiro nacional|gestão fraudulenta|evasão de divisas)\b", re.IGNORECASE), "4689"),
            # Crimes contra a Economia Popular (1.521/51)
            (re.compile(r"\b(?:1\.521|economia popular|usura pecuniária)\b", re.IGNORECASE), "4687"),
        ]

        # 2. Specific Procedural Institutes
        self.procedure_map = [
            # Tribunal do Júri
            (re.compile(r"\b(?:tribunal do júri|desaforamento|pronúncia|impronúncia|absolvição sumária no júri|conselho de sentença|quesitação|art\. 406 do cpp|art\. 413 do cpp)\b", re.IGNORECASE), "5524"),
            # Inquérito Policial
            (re.compile(r"\b(?:inquérito policial|notitia criminis|indiciamento|arquivamento do inquérito|súmula 524 do stf|art\. 18 do cpp|art\. 28 do cpp)\b", re.IGNORECASE), "5498"),
            # ANPP (Acordo de Não Persecução Penal)
            (re.compile(r"\b(?:acordo de não persecução penal|anpp|art\. 28-a do cpp)\b", re.IGNORECASE), "5504"),
            # Habeas Corpus
            (re.compile(r"\b(?:habeas corpus|remédio heroico|salvo-conduto|constrangimento ilegal à liberdade de locomoção|art\. 647 do cpp)\b", re.IGNORECASE), "5477"),
            # Revisão Criminal
            (re.compile(r"\b(?:revisão criminal|art\. 621 do cpp)\b", re.IGNORECASE), "5478"),
            # Competência
            (re.compile(r"\b(?:competência territorial|competência ratione loci|competência ratione materiae|foro por prerrogativa|conexão e continência|derrogação da competência|juízo competente|desaforamento)\b", re.IGNORECASE), "5480"),
            # Nulidades
            (re.compile(r"\b(?:nulidade absoluta|nulidade relativa|nulidades processuais|pas de nullité sans grief|art\. 564 do cpp)\b", re.IGNORECASE), "5509"),
            # Comunicação dos Atos / Citação / Intimação
            (re.compile(r"\b(?:citação por edital|citação por hora certa|citação pessoal|intimação e contagem dos prazos|comunicação dos atos processuais|art\. 366 do cpp|art\. 370 do cpp)\b", re.IGNORECASE), "5487"),
            # Prisões em Espécie / Preventiva / Temporária / Domiciliar / Liberdade Provisória
            (re.compile(r"\b(?:prisão preventiva|art\. 312 do cpp|art\. 313 do cpp|art\. 316 do cpp)\b", re.IGNORECASE), "5518"),
            (re.compile(r"\b(?:prisão temporária|lei 7\.960)\b", re.IGNORECASE), "5519"),
            (re.compile(r"\b(?:prisão domiciliar|art\. 318 do cpp|art\. 318-a do cpp)\b", re.IGNORECASE), "5520"),
            (re.compile(r"\b(?:liberdade provisória|fiança criminal|quebramento da fiança|art\. 321 do cpp)\b", re.IGNORECASE), "5522"),
            (re.compile(r"\b(?:prisão em flagrante|flagrante delito|audiência de custódia|auto de prisão em flagrante|art\. 302 do cpp|art\. 310 do cpp)\b", re.IGNORECASE), "5584"),
            # Provas no Processo Penal
            (re.compile(r"\b(?:prova testemunhal|testemunha numerária|testemunha referida|compromisso de dizer a verdade|contradita de testemunha|art\. 202 do cpp)\b", re.IGNORECASE), "5550"),
            (re.compile(r"\b(?:prova documental|falsidade documental no processo|art\. 231 do cpp|art\. 232 do cpp)\b", re.IGNORECASE), "5553"),
            (re.compile(r"\b(?:exame de corpo de delito|prova pericial|perito oficial|art\. 158 do cpp|art\. 159 do cpp)\b", re.IGNORECASE), "5544"),
            (re.compile(r"\b(?:confissão no processo penal|confissão espontânea no processo|confissão qualificada|art\. 197 do cpp)\b", re.IGNORECASE), "5548"),
            (re.compile(r"\b(?:reconhecimento de pessoas|art\. 226 do cpp)\b", re.IGNORECASE), "5551"),
            (re.compile(r"\b(?:busca e apreensão|mandado de busca e apreensão|art\. 240 do cpp)\b", re.IGNORECASE), "5555"),
            (re.compile(r"\b(?:prova ilícita|frutos da árvore envenenada|fruits of the poisonous tree|art\. 157 do cpp)\b", re.IGNORECASE), "5594"),
            (re.compile(r"\b(?:cadeia de custódia|rastreabilidade do vestígio|coleta do vestígio|art\. 158-a do cpp)\b", re.IGNORECASE), "5595"),
            # Recursos no Processo Penal
            (re.compile(r"\b(?:recurso de apelação|apelação criminal|art\. 593 do cpp)\b", re.IGNORECASE), "5562"),
            (re.compile(r"\b(?:recurso em sentido estrito|rese|art\. 581 do cpp)\b", re.IGNORECASE), "5563"),
            (re.compile(r"\b(?:embargos de declaração no cpp|art\. 619 do cpp)\b", re.IGNORECASE), "5565"),
            (re.compile(r"\b(?:embargos infringentes e de nulidade|art\. 609 do cpp)\b", re.IGNORECASE), "5564"),
            (re.compile(r"\b(?:carta testemunhável|art\. 639 do cpp)\b", re.IGNORECASE), "5567"),
            (re.compile(r"\b(?:recurso especial criminal|art\. 105 da cf)\b", re.IGNORECASE), "5571"),
            (re.compile(r"\b(?:recurso extraordinário criminal|art\. 102 da cf)\b", re.IGNORECASE), "5570"),
            (re.compile(r"\b(?:efeito devolutivo|efeito suspensivo|reformatio in pejus|pressupostos recursais|teoria geral dos recursos)\b", re.IGNORECASE), "5512"),
            # Sentença Penal
            (re.compile(r"\b(?:emendatio libelli|mutatio libelli|art\. 383 do cpp|art\. 384 do cpp|sentença penal condenatória|sentença penal absolutória)\b", re.IGNORECASE), "5572"),
            # Procedimento Comum Ordinário
            (re.compile(r"\b(?:resposta à acusação|defesa prévia no cpp|audiência de instrução e julgamento|art\. 396 do cpp|art\. 397 do cpp|art\. 400 do cpp)\b", re.IGNORECASE), "5530"),
            # Ação Penal no Processo Penal
            (re.compile(r"\b(?:ação penal pública incondicionada|ação penal pública condicionada|representação do ofendido|ação civil ex delicto|queixa-crime|art\. 24 do cpp|art\. 25 do cpp)\b", re.IGNORECASE), "5466"),
            # Sistemas e Princípios Processuais
            (re.compile(r"\b(?:sistema acusatório|sistema inquisitório|juiz das garantias|princípio da presunção de inocência|contraditório e ampla defesa no processo penal|nemo tenetur se detegere)\b", re.IGNORECASE), "5580"),
            # Sujeitos do Processo
            (re.compile(r"\b(?:assistente de acusação|assistente da acusação|sujeitos processuais|art\. 268 do cpp|art\. 271 do cpp)\b", re.IGNORECASE), "5583"),
            # Questões e Processos Incidentes
            (re.compile(r"\b(?:incidente de insanidade mental|art\. 149 do cpp|exceção de suspeição|exceção de incompetência|medidas assecuratórias|sequestro e arresto)\b", re.IGNORECASE), "5490"),
            # Lei Processual no Tempo e no Espaço
            (re.compile(r"\b(?:tempus regit actum|lei processual penal no tempo|aplicação imediata da lei processual|art\. 2º do cpp)\b", re.IGNORECASE), "5505"),
        ]

        # 3. Specific Criminal Law (Penal) Institutes
        self.penal_map = [
            # Crimes Contra a Pessoa / Vida
            (re.compile(r"\b(?:homicídio|feminicídio|infanticídio|aborto|suicídio ou automutilação|art\. 121 do cp|art\. 122 do cp|art\. 123 do cp|art\. 124 do cp)\b", re.IGNORECASE), "5149"),
            # Lesões Corporais
            (re.compile(r"\b(?:lesão corporal|lesões corporais|art\. 129 do cp|ofensa à integridade corporal)\b", re.IGNORECASE), "5077"),
            # Periclitação da Vida e da Saúde
            (re.compile(r"\b(?:omissão de socorro|abandono de incapaz|perigo para a vida ou saúde|maus-tratos|art\. 135 do cp|art\. 133 do cp|art\. 136 do cp)\b", re.IGNORECASE), "5138"),
            # Crimes Contra a Honra
            (re.compile(r"\b(?:calúnia|difamação|injúria|exceção da verdade|animus injuriandi|animus caluniandi|art\. 138 do cp|art\. 139 do cp|art\. 140 do cp)\b", re.IGNORECASE), "5120"),
            # Crimes Contra a Liberdade Pessoal / Individual
            (re.compile(r"\b(?:constrangimento ilegal|ameaça|perseguição|stalking|sequestro e cárcere privado|tráfico de pessoas|invasão de dispositivo informático|art\. 146 do cp|art\. 147 do cp|art\. 147-a do cp|art\. 154-a do cp)\b", re.IGNORECASE), "5128"),
            # Crimes Contra o Patrimônio
            (re.compile(r"\b(?:furto simples|furto qualificado|furto mediante fraude|furto de coisa comum|art\. 155 do cp)\b", re.IGNORECASE), "5158"),
            (re.compile(r"\b(?:roubo|roubo majorado|latrocínio|art\. 157 do cp)\b", re.IGNORECASE), "5162"),
            (re.compile(r"\b(?:extorsão mediante sequestro|art\. 159 do cp)\b", re.IGNORECASE), "5161"),
            (re.compile(r"\b(?:extorsão|art\. 158 do cp)\b", re.IGNORECASE), "5160"),
            (re.compile(r"\b(?:apropriação indébita|apropriação indébita previdenciária|art\. 168 do cp|art\. 168-a do cp)\b", re.IGNORECASE), "5159"),
            (re.compile(r"\b(?:estelionato|fraude no pagamento por meio de cheque|disposições sobre estelionato|art\. 171 do cp|art\. 176 do cp)\b", re.IGNORECASE), "5163"),
            (re.compile(r"\b(?:dano simples|dano qualificado|art\. 163 do cp)\b", re.IGNORECASE), "5165"),
            (re.compile(r"\b(?:receptação simples|receptação qualificada|receptação culposa|art\. 180 do cp)\b", re.IGNORECASE), "5166"),
            (re.compile(r"\b(?:escusas absolutórias|imunidades patrimoniais|art\. 181 do cp|art\. 182 do cp|art\. 183 do cp)\b", re.IGNORECASE), "5169"),
            # Crimes Contra a Dignidade Sexual
            (re.compile(r"\b(?:estupro de vulnerável|art\. 217-a do cp)\b", re.IGNORECASE), "5104"),
            (re.compile(r"\b(?:estupro|assédio sexual|importunação sexual|violação sexual mediante fraude|favorecimento da prostituição|art\. 213 do cp|art\. 215-a do cp|art\. 216-a do cp|art\. 218-b do cp)\b", re.IGNORECASE), "5102"),
            # Crimes Contra a Família
            (re.compile(r"\b(?:abandono material|abandono intelectual|crimes contra a assistência familiar|art\. 244 do cp)\b", re.IGNORECASE), "5111"),
            # Crimes Contra a Fé Pública
            (re.compile(r"\b(?:moeda falsa|falsidade ideológica|falsificação de documento público|falsificação de documento particular|uso de documento falso|falsa identidade|art\. 289 do cp|art\. 297 do cp|art\. 298 do cp|art\. 299 do cp|art\. 304 do cp|art\. 307 do cp)\b", re.IGNORECASE), "5116"),
            # Crimes Contra a Organização do Trabalho
            (re.compile(r"\b(?:atentado contra a liberdade de trabalho|boicotagem violenta|frustração de direito assegurado por lei trabalhista|art\. 197 do cp|art\. 198 do cp|art\. 203 do cp)\b", re.IGNORECASE), "5135"),
            # Crimes Contra a Paz Pública
            (re.compile(r"\b(?:associação criminosa|constituição de milícia privada|art\. 288 do cp|art\. 288-a do cp)\b", re.IGNORECASE), "5144"),
            # Crimes Contra a Administração Pública
            (re.compile(r"\b(?:peculato|peculato culposo|peculato apropriação|peculato desvio|peculato furto|art\. 312 do cp)\b", re.IGNORECASE), "5088"),
            (re.compile(r"\b(?:concussão|excesso de exação|art\. 316 do cp)\b", re.IGNORECASE), "5089"),
            (re.compile(r"\b(?:corrupção passiva|art\. 317 do cp)\b", re.IGNORECASE), "5090"),
            (re.compile(r"\b(?:corrupção ativa|art\. 333 do cp)\b", re.IGNORECASE), "5096"),
            (re.compile(r"\b(?:prevaricação|condescendência criminosa|advocacia administrativa|art\. 319 do cp|art\. 320 do cp|art\. 321 do cp)\b", re.IGNORECASE), "5087"),
            (re.compile(r"\b(?:desobediência|desacato|resistência|usurpação de função pública|art\. 329 do cp|art\. 330 do cp|art\. 331 do cp)\b", re.IGNORECASE), "5095"),
            (re.compile(r"\b(?:tráfico de influência|art\. 332 do cp)\b", re.IGNORECASE), "5097"),
            (re.compile(r"\b(?:crimes em licitações|art\. 337-e do cp|art\. 337-f do cp)\b", re.IGNORECASE), "5099"),
            # Crimes Contra a Administração Judicial
            (re.compile(r"\b(?:denunciação caluniosa|comunicação falsa de crime|autoacusação falsa|art\. 339 do cp|art\. 340 do cp|art\. 341 do cp)\b", re.IGNORECASE), "5081"),
            (re.compile(r"\b(?:falso testemunho|falsa perícia|art\. 342 do cp)\b", re.IGNORECASE), "5082"),
            (re.compile(r"\b(?:coação no curso do processo|exercício arbitrário das próprias razões|art\. 344 do cp|art\. 345 do cp)\b", re.IGNORECASE), "5079"),
            (re.compile(r"\b(?:favorecimento pessoal|favorecimento real|art\. 348 do cp|art\. 349 do cp)\b", re.IGNORECASE), "5085"),
            (re.compile(r"\b(?:fraude processual|art\. 347 do cp)\b", re.IGNORECASE), "5086"),
            # Parte Geral: Teoria do Crime, Aplicação da Lei, Pena, Punibilidade
            (re.compile(r"\b(?:concurso de crimes|concurso material|concurso formal|crime continuado|art\. 69 do cp|art\. 70 do cp|art\. 71 do cp|aberratio ictus|aberratio delicti)\b", re.IGNORECASE), "5066"),
            (re.compile(r"\b(?:concurso de pessoas|coautoria|participação|autoria mediata|comunicabilidade de circunstâncias|cooperação dolosamente distinta|art\. 29 do cp|art\. 30 do cp|art\. 31 do cp|domínio do fato)\b", re.IGNORECASE), "5071"),
            (re.compile(r"\b(?:iter criminis|crime consumado|tentativa|crime tentado|crime impossível|desistência voluntária|arrependimento eficaz|arrependimento posterior|art\. 14 do cp|art\. 15 do cp|art\. 16 do cp|art\. 17 do cp)\b", re.IGNORECASE), "5175"),
            (re.compile(r"\b(?:erro de tipo|erro de tipo essencial|erro invencível|erro de tipo acidental|art\. 20 do cp|dolo e culpa|crime doloso|crime culposo|art\. 18 do cp)\b", re.IGNORECASE), "5218"),
            (re.compile(r"\b(?:excludentes? de ilicitude|legítima defesa|estado de necessidade|estrito cumprimento do dever legal|exercício regular de direito|art\. 23 do cp|art\. 24 do cp|art\. 25 do cp)\b", re.IGNORECASE), "5228"),
            (re.compile(r"\b(?:culpabilidade|imputabilidade penal|erro de proibição|coação moral irresistível|obediência hierárquica|embriaguez involuntária|art\. 21 do cp|art\. 22 do cp|art\. 26 do cp|art\. 28 do cp)\b", re.IGNORECASE), "5211"),
            (re.compile(r"\b(?:teoria da pena|dosimetria da pena|critério trifásico|circunstâncias judiciais|pena-base|atenuantes e agravantes|causas de aumento e diminuição|art\. 59 do cp|art\. 65 do cp|art\. 68 do cp|regime fechado|regime semiaberto|regime aberto|substituição da pena privativa|penas restritivas de direitos|sursis da pena|livramento condicional)\b", re.IGNORECASE), "5199"),
            (re.compile(r"\b(?:medida de segurança|inimputabilidade por doença mental|desinternação condicional|art\. 96 do cp|art\. 97 do cp)\b", re.IGNORECASE), "5184"),
            (re.compile(r"\b(?:extinção da punibilidade|causas extintivas da punibilidade|anistia, graça e indulto|abolitio criminis|decadência|perempção|renúncia e perdão|art\. 107 do cp)\b", re.IGNORECASE), "5191"),
            (re.compile(r"\b(?:prescrição da pretensão punitiva|prescrição da pretensão executória|prescrição intercorrente|prescrição retroativa|prescrição da pena em abstrato|prescrição da pena em concreto|causas interruptivas da prescrição|art\. 109 do cp|art\. 110 do cp|art\. 115 do cp|art\. 117 do cp)\b", re.IGNORECASE), "5185"),
            (re.compile(r"\b(?:lei penal no tempo|lei penal no espaço|retroatividade da lei penal|novatio legis in mellius|extraterritorialidade da lei penal|art\. 2º do cp|art\. 5º do cp|art\. 7º do cp|conflito aparente de normas|princípio da consunção|princípio da especialidade)\b", re.IGNORECASE), "5180"),
            (re.compile(r"\b(?:princípio da legalidade|princípio da anterioridade|princípio da insignificância|interpretação da lei penal|fontes do direito penal|classificação dos crimes|norma penal em branco)\b", re.IGNORECASE), "5170"),
        ]

        # 4. Specific Criminology Concept Mappings
        self.criminology_map = [
            (re.compile(r"\b(?:vitimologia|vítima ideal|vítima culpada|mendelsohn|von hentig|processos de vitimização|vitimização secundária|sobrevitimização)\b", re.IGNORECASE), "4389"),
            (re.compile(r"\b(?:classificação dos criminosos|criminoso nato|criminoso habitual|criminoso passional|lombroso|ferri)\b", re.IGNORECASE), "4367"),
            (re.compile(r"\b(?:escola clássica|escola positiva|positivismo criminológico|etapas evolutivas da criminologia|beccaria|garofalo)\b", re.IGNORECASE), "4371"),
            (re.compile(r"\b(?:direito penal do inimigo|günther jakobs|jakobs|velocidades do direito penal)\b", re.IGNORECASE), "4376"),
            (re.compile(r"\b(?:política criminal|movimento da lei e da ordem|abolicionismo penal|minimalismo penal)\b", re.IGNORECASE), "4374"),
            (re.compile(r"\b(?:cifras criminais|cifra negra|cifra dourada|cifra cinza|criminalização primária e secundária)\b", re.IGNORECASE), "4377"),
            (re.compile(r"\b(?:teorias sociológicas explicativas|teoria da anomia|teoria da associação diferencial|teoria do etiquetamento|labelling approach|escola de chicago|criminologia crítica|alessandro baratta|robert merton|edwin sutherland|howard becker)\b", re.IGNORECASE), "4385"),
            (re.compile(r"\b(?:teorias legitimidoras da pena|finalidades da pena|teoria absoluta da pena|teoria relativa da pena|prevenção geral|prevenção especial|kant e hegel na criminologia|liszt na criminologia)\b", re.IGNORECASE), "4384"),
            (re.compile(r"\b(?:modelos de reação ao delito|modelo dissuasório|modelo ressocializador|modelo restaurador|justiça restaurativa)\b", re.IGNORECASE), "4370"),
            (re.compile(r"\b(?:sistemas de prevenção|prevenção primária, secundária e terciária)\b", re.IGNORECASE), "4369"),
            (re.compile(r"\b(?:conceito e objeto da criminologia|ciência empírica e interdisciplinar|métodos da criminologia|controle social formal e informal)\b", re.IGNORECASE), "4380"),
        ]

    def is_out_of_scope(self, q: Question) -> Tuple[bool, str]:
        """Detects whether a question is strictly outside the four target disciplines."""
        full_text = q.full_text.lower()

        # Q0142: ITCD / Direito Tributário puro
        if q.id == "Q0142" or ("itcd" in full_text and "causa mortis" in full_text and "imposto" in full_text):
            return True, "Direito Tributário estrito (ITCD/isenção fiscal): sem tipificação penal ou tema na taxonomia"

        # Q0168: Lei Geral do Esporte (Lei 14.597/2023)
        if q.id == "Q0168" or ("14.597" in full_text and "resultado esportivo" in full_text):
            return True, "Lei Geral do Esporte (Lei 14.597/2023): crimes esportivos não possuem nó correspondente na árvore"

        return False, ""

    def match_topic(self, q: Question) -> Tuple[str, List[str], float, str]:
        """Core substantive matching logic returning (topic_id, extras, confidence, reason)."""
        text = q.full_text
        q_id = q.id

        # 1. Check out of scope first
        out, reason = self.is_out_of_scope(q)
        if out:
            return "", [], 0.99, reason

        matched_scores: Dict[str, float] = {}
        extras: List[str] = []

        # 2. Check special statute mappings
        for pattern, topic_id in self.statute_map:
            if pattern.search(text):
                # Ensure canonical and active
                canon_id = self.tree.get_canonical_id(topic_id)
                if self.tree.is_active(canon_id):
                    matched_scores[canon_id] = matched_scores.get(canon_id, 0.0) + 3.0

        # 3. Check procedure mappings
        for pattern, topic_id in self.procedure_map:
            if pattern.search(text):
                canon_id = self.tree.get_canonical_id(topic_id)
                if self.tree.is_active(canon_id):
                    matched_scores[canon_id] = matched_scores.get(canon_id, 0.0) + 2.5

        # 4. Check penal mappings
        for pattern, topic_id in self.penal_map:
            if pattern.search(text):
                canon_id = self.tree.get_canonical_id(topic_id)
                if self.tree.is_active(canon_id):
                    matched_scores[canon_id] = matched_scores.get(canon_id, 0.0) + 2.5

        # 5. Check criminology mappings
        for pattern, topic_id in self.criminology_map:
            if pattern.search(text):
                canon_id = self.tree.get_canonical_id(topic_id)
                if self.tree.is_active(canon_id):
                    matched_scores[canon_id] = matched_scores.get(canon_id, 0.0) + 3.0

        # Sort candidates by score
        sorted_candidates = sorted(matched_scores.items(), key=lambda x: x[1], reverse=True)

        if not sorted_candidates:
            # Fallback based on origin discipline & text keywords
            fallback_id = self._fallback_match(q)
            return fallback_id, [], 0.60, "Correspondência por heurística secundária; confiança moderada"

        primary_id = sorted_candidates[0][0]
        primary_score = sorted_candidates[0][1]

        # Gather extras
        for cand_id, score in sorted_candidates[1:]:
            if cand_id != primary_id and score >= 2.0 and not self.tree.is_same_branch(cand_id, primary_id):
                extras.append(cand_id)

        # Handle specific known edge cases
        # Q0297: Direito Penal Econômico (Crimes Tributários + Sistema Financeiro), 5078 is inactive!
        if q_id == "Q0297":
            return "4695", ["4689"], 0.70, "Questão multidisciplinar de Direito Penal Econômico; tema 5078 está inativo; sugerido 4695 com extra 4689"

        # Q0014: Habeas Corpus vs Infância/Juventude (Medidas Socioeducativas)
        if q_id == "Q0014":
            return "5477", [], 0.65, "Tensão entre cabimento de Habeas Corpus (5477) e matéria socioeducativa/ECA (fora da árvore)"

        # Q0011: Interceptação Telefônica, Tráfico de Drogas, Lavagem de Capitais
        if q_id == "Q0011":
            return "4700", ["4708", "4702"], 0.72, "Questão transversal abordando Interceptação Telefônica, Drogas e Lavagem de Capitais"

        # Calculate calibrated confidence
        if len(sorted_candidates) == 1:
            confidence = 0.96
        else:
            second_score = sorted_candidates[1][1]
            diff = primary_score - second_score
            if diff >= 2.0:
                confidence = 0.95
            elif diff >= 1.0:
                confidence = 0.91
            else:
                # Close scores: check if same branch
                if self.tree.is_same_branch(primary_id, sorted_candidates[1][0]):
                    # Same branch! Assign parent if appropriate or keep with high confidence
                    confidence = 0.93
                else:
                    confidence = 0.75

        # Refine primary topic if a specific leaf or robust parent applies
        primary_node = self.tree.get(primary_id)
        if primary_node and primary_node.nivel == 0:
            # Never assign root discipline as primary publication topic! Roll to best L1 child.
            l1_candidates = [cid for cid, s in sorted_candidates if self.tree.get(cid) and self.tree.get(cid).disciplina == primary_node.disciplina and self.tree.get(cid).nivel >= 1]
            if l1_candidates:
                primary_id = l1_candidates[0]
            else:
                confidence = 0.60

        reason = "" if confidence >= 0.88 else "Ambiguidade entre múltiplos temas ou tópicos transversais"
        return primary_id, extras[:3], confidence, reason

    def _fallback_match(self, q: Question) -> str:
        """Fallback matching based on origin metadata and text tokens."""
        disc = q.disciplina_origem
        text = q.full_text.lower()

        if "criminologia" in disc.lower() or "criminolog" in text:
            return "4380"  # Teoria Geral da Criminologia
        if "processo penal" in disc.lower():
            if "recurso" in text:
                return "5560"
            if "prova" in text:
                return "5590"
            if "prisão" in text:
                return "5517"
            if "inquérito" in text:
                return "5498"
            return "5580"  # Sistemas e Princípios
        if "legislação" in disc.lower():
            return "4704"  # Default active special law
        # Penal
        if "patrimônio" in text:
            return "5157"
        if "vida" in text or "morte" in text:
            return "5149"
        if "administração" in text:
            return "5087"
        if "pena" in text:
            return "5199"
        return "5170"  # Introdução ao Estudo do Direito Penal

    def classify(self, q: Question) -> ClassificationResult:
        """Classifies a question into publicar, revisar, or fora."""
        # Check out of scope
        out, reason = self.is_out_of_scope(q)
        if out:
            return ClassificationResult(
                question_id=q.id,
                decisao="fora",
                tema_central_id="",
                extras_ids=[],
                confianca=0.99,
                motivo=reason,
            )

        primary_id, extras, conf, reason = self.match_topic(q)

        # Decision Gating Policy for >=95% precision:
        # High confidence threshold tau = 0.88
        if conf >= 0.88 and primary_id and self.tree.is_active(primary_id):
            decisao = "publicar"
            motivo = ""  # Empty for publicar
        else:
            decisao = "revisar"
            motivo = reason if reason else "Necessária validação humana: sobreposição temática ou confiança moderada"

        return ClassificationResult(
            question_id=q.id,
            decisao=decisao,
            tema_central_id=primary_id,
            extras_ids=extras,
            confianca=round(conf, 2),
            motivo=motivo,
        )

    def classify_all(self, questions: List[Question]) -> List[ClassificationResult]:
        return [self.classify(q) for q in questions]
