"""Comprehensive analysis and classification auditor for all 359 questions.

Combines statute extraction, subject-heading detection, comando analysis,
alternative contrasting analysis, smart parent rollup, and strict gating.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.preprocessor import Question, QuestionPreprocessor
from src.taxonomy import TaxonomyTree, TopicNode


def build_question_analysis():
    tree = TaxonomyTree()
    questions = QuestionPreprocessor.load_dataset()

    print(f"Loaded {len(questions)} questions and {len(tree.get_active_topics())} active topics.")
    return tree, questions


if __name__ == "__main__":
    build_question_analysis()

