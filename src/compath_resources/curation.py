import logging
import os
from difflib import SequenceMatcher
from typing import Mapping, Tuple

import itertools as itt
import pandas as pd
from tqdm import tqdm

from bio2bel.compath import get_compath_manager_classes

logger = logging.getLogger(__name__)


def make_similarity_matricies(
    directory: str,
    minimum_gene_set_similarity: float = 0.8,
    minimum_string_similarity: float = 0.00,
) -> Mapping[Tuple[str, str], pd.DataFrame]:
    """

    :param directory:
    :param minimum_gene_set_similarity:
    :param minimum_string_similarity:
    :return:
    """
    os.makedirs(directory, exist_ok=True)

    database = {}
    mappings = {}
    for name, manager_cls in get_compath_manager_classes().items():
        logger.info('loading %s', name)
        manager = manager_cls()
        if not manager.is_populated():
            logger.warning('not populated %s', name)
            continue
        logger.info('getting pathways from %s', name)
        database[name] = manager.get_pathway_id_to_symbols()
        mappings[name] = manager.get_pathway_id_name_mapping()

    rv = {}
    for (a_name, a_sets), (b_name, b_sets) in itt.combinations(database.items(), r=2):
        logger.info('calculating similarities between %s and %s', a_name, b_name)
        a_mappings, b_mappings = mappings[a_name], mappings[b_name]

        rows = []
        it = itt.product(a_sets.items(), b_sets.items())
        it = tqdm(it, total=len(a_sets) * len(b_sets))
        for (a_pathway_id, a_set), (b_pathway_id, b_set) in it:
            gene_similarity = calculate_jaccard(a_set, b_set)
            if gene_similarity < minimum_gene_set_similarity:
                continue

            sequence_matcher = SequenceMatcher(None, a_name, b_name)
            string_similarity = sequence_matcher.ratio()
            if string_similarity < minimum_string_similarity:
                continue

            rows.append((
                a_pathway_id, a_mappings[a_pathway_id],
                b_pathway_id, b_mappings[b_pathway_id],
                gene_similarity, string_similarity,
            ))

        rv[a_name, b_name] = df = pd.DataFrame(
            rows,
            columns=[f'{a_name}_id', f'{a_name}_name', f'{b_name}_id',
                     f'{b_name}_name', 'gene_set_similarity', 'string_similarity'],
        ).sort_values([f'{a_name}_id', 'gene_set_similarity'], ascending=False)

        path = os.path.join(directory, f'{a_name}_{b_name}.tsv')
        df.to_csv(path, sep='\t', index=False)

    return rv


def calculate_jaccard(set_1, set_2):
    """calculates jaccard similarity between two sets

    :param set set_1: set 1
    :param set set_2: set 2
    :returns similarity
    :rtype: float
    """
    intersection = len(set_1.intersection(set_2))
    smaller_set = min(len(set_1), len(set_2))

    return intersection / smaller_set


if __name__ == '__main__':
    make_similarity_matricies(os.path.join(os.path.expanduser('~'), 'Desktop', 'compath-mappings'))
