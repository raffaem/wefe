import pytest

from wefe.utils import load_weat_w2v, run_queries, create_ranking, calculate_ranking_correlations
from wefe.datasets import load_weat
from wefe.query import Query
from wefe.word_embedding_model import WordEmbeddingModel
from wefe.metrics import WEAT

from gensim.models import Word2Vec, KeyedVectors
import gensim.downloader as api
import numpy as np
import pandas as pd


def test_load_weat_w2v():
    weat_w2v = load_weat_w2v()
    assert isinstance(weat_w2v, KeyedVectors)
    assert len(weat_w2v.vocab.keys()) == 347

    for vocab in weat_w2v.vocab:
        assert isinstance(weat_w2v[vocab], np.ndarray)


@pytest.fixture
def queries_and_models():
    word_sets = load_weat()

    # Create gender queries
    gender_query_1 = Query(
        [word_sets['male_terms'], word_sets['female_terms']],
        [word_sets['career'], word_sets['family']],
        ['Male terms', 'Female terms'], ['Career', 'Family'])
    gender_query_2 = Query(
        [word_sets['male_terms'], word_sets['female_terms']],
        [word_sets['science'], word_sets['arts']],
        ['Male terms', 'Female terms'], ['Science', 'Arts'])
    gender_query_3 = Query(
        [word_sets['male_terms'], word_sets['female_terms']],
        [word_sets['math'], word_sets['arts_2']],
        ['Male terms', 'Female terms'], ['Math', 'Arts'])

    # Create ethnicity queries
    test_query_1 = Query([word_sets['insects'], word_sets['flowers']],
                         [word_sets['pleasant_5'], word_sets['unpleasant_5']],
                         ['Flowers', 'Insects'], ['Pleasant', 'Unpleasant'])

    test_query_2 = Query([word_sets['weapons'], word_sets['instruments']],
                         [word_sets['pleasant_5'], word_sets['unpleasant_5']],
                         ['Instruments', 'Weapons'],
                         ['Pleasant', 'Unpleasant'])

    gender_queries = [gender_query_1, gender_query_2, gender_query_3]
    negative_test_queries = [test_query_1, test_query_2]

    weat_w2v = load_weat_w2v()
    dummy_model_1 = weat_w2v
    dummy_model_2 = weat_w2v
    dummy_model_3 = weat_w2v

    models = [
        WordEmbeddingModel(dummy_model_1, 'dummy_model_1'),
        WordEmbeddingModel(dummy_model_2, 'dummy_model_2'),
        WordEmbeddingModel(dummy_model_3, 'dummy_model_3')
    ]
    return gender_queries, negative_test_queries, models


def test_run_query_input_validation(queries_and_models):

    # -----------------------------------------------------------------
    # Input checks
    # -----------------------------------------------------------------

    # Load the inputs of the fixture
    gender_queries, _, models = queries_and_models

    with pytest.raises(
            TypeError,
            match='queries parameter must be a list or a numpy array*'):
        run_queries(WEAT, None, None)

    with pytest.raises(
            Exception,
            match='queries list must have at least one query instance*'):
        run_queries(WEAT, [], None)

    with pytest.raises(TypeError,
                       match='item on index 0 must be a Query instance*'):
        run_queries(WEAT, [None, None], None)

    with pytest.raises(TypeError,
                       match='item on index 3 must be a Query instance*'):
        run_queries(WEAT, gender_queries + [None], None)

    with pytest.raises(
            TypeError, match=
            'word_embeddings_models parameter must be a list or a numpy array*'
    ):
        run_queries(WEAT, gender_queries, None)

    with pytest.raises(
            Exception, match=
            'word_embeddings_models parameter must be a non empty list or numpy array*'
    ):
        run_queries(WEAT, gender_queries, [])

    with pytest.raises(
            TypeError,
            match='item on index 0 must be a WordEmbeddingModel instance*'):
        run_queries(WEAT, gender_queries, [None])

    with pytest.raises(
            TypeError,
            match='item on index 3 must be a WordEmbeddingModel instance*'):
        run_queries(WEAT, gender_queries, models + [None])

    with pytest.raises(
            TypeError, match=
            'When queries_set_name parameter is provided, it must be a non-empty string*'
    ):
        run_queries(WEAT, gender_queries, models, queries_set_name=None)

    with pytest.raises(
            TypeError, match=
            'When queries_set_name parameter is provided, it must be a non-empty string*'
    ):
        run_queries(WEAT, gender_queries, models, queries_set_name="")

    with pytest.raises(
            TypeError, match=
            'run_experiment_params must be a dict with a params for the metric*'
    ):
        run_queries(WEAT, gender_queries, models, metric_params=None)

    with pytest.raises(
            Exception,
            match='include_average_by_embedding param must be any of*'):
        run_queries(WEAT, gender_queries, models,
                    include_average_by_embedding=12)

    with pytest.raises(Exception,
                       match='average_with_abs_values param must be boolean*'):
        run_queries(WEAT, gender_queries, models, average_with_abs_values=None)


def test_run_query(queries_and_models):

    # -----------------------------------------------------------------
    # Basic run_queries execution
    # -----------------------------------------------------------------

    # Load the inputs of the fixture
    gender_queries, negative_test_queries, models = queries_and_models

    results = run_queries(WEAT, gender_queries, models)

    assert isinstance(results, pd.DataFrame)
    assert results.shape == (3, 4)

    expected_cols = [
        'Male terms and Female terms wrt Career and Family',
        'Male terms and Female terms wrt Science and Arts',
        'Male terms and Female terms wrt Math and Arts',
        'WEAT: Unnamed queries set average score'
    ]

    for given_col, expected_col in zip(results.columns, expected_cols):
        assert given_col == expected_col

    expected_index = ['dummy_model_1', 'dummy_model_2', 'dummy_model_3']

    for given_idx, expected_idx in zip(results.index, expected_index):
        assert given_idx, expected_idx

    # Query set name
    results = run_queries(WEAT, gender_queries, models,
                          queries_set_name='Gender Queries')
    assert results.columns.values[-1] == 'WEAT: Gender Queries average score'

    # lost_vocabulary_threshold...
    word_sets = load_weat()
    dummy_query_1 = Query([['bla', 'ble', 'bli'], word_sets['insects']],
                          [word_sets['pleasant_9'], word_sets['unpleasant_9']])

    results = run_queries(WEAT, gender_queries + [dummy_query_1], models,
                          lost_vocabulary_threshold=0.1)
    assert results.shape == (3, 5)
    assert results.isnull().any().any()

    # metric param...
    results = run_queries(WEAT, gender_queries, models,
                          metric_params={'return_effect_size': True})
    assert results.shape == (3, 4)

    # include_average_by_embedding..
    results = run_queries(WEAT, gender_queries, models,
                          include_average_by_embedding='only')
    assert results.shape == (3, 1)

    results = run_queries(WEAT, gender_queries, models,
                          include_average_by_embedding='include')
    assert results.shape == (3, 4)
    avg = results.values[:, 3]
    values = results.values[:, 0:3]
    calc_avg = np.mean(values, axis=1)
    assert np.array_equal(avg, calc_avg)

    results = run_queries(WEAT, gender_queries, models,
                          include_average_by_embedding=None)
    assert results.shape == (3, 3)

    results = run_queries(WEAT, negative_test_queries, models,
                          include_average_by_embedding='only',
                          average_with_abs_values=False)
    assert results.shape == (3, 1)
    for row in results.values:
        for val in row:
            assert val <= 0


def test_ranking_results(queries_and_models):

    gender_queries, negative_test_queries, models = queries_and_models
    results_gender = run_queries(WEAT, gender_queries, models,
                                 queries_set_name='Gender Queries',
                                 include_average_by_embedding=None)
    results_test = run_queries(WEAT, negative_test_queries, models,
                               queries_set_name='Negative Test Queries',
                               include_average_by_embedding='include')

    with pytest.raises(
            TypeError, match=
            'All elements of results_dataframes must be a pandas Dataframe instance*'
    ):
        create_ranking([None, results_gender, results_test])

    with pytest.raises(Exception, match='There is no average column in*'):
        create_ranking([results_gender, results_test])

    results_gender = run_queries(WEAT, gender_queries, models,
                                 queries_set_name='Gender Queries',
                                 include_average_by_embedding='include')
    results_test = run_queries(WEAT, negative_test_queries, models,
                               queries_set_name='Negative Test Queries',
                               include_average_by_embedding=None)

    with pytest.raises(Exception, match='There is no average column in*'):
        create_ranking([results_gender, results_test])

    results_gender = run_queries(WEAT, gender_queries, models,
                                 queries_set_name='Gender Queries',
                                 include_average_by_embedding='include')
    results_test = run_queries(WEAT, negative_test_queries, models,
                               queries_set_name='Negative Test Queries',
                               include_average_by_embedding='include')

    ranking = create_ranking([results_gender, results_test])
    assert ranking.shape == (3, 2)

    for row in ranking.values:
        for val in row:
            assert val <= 3 and val >= 1


def test_correlations(queries_and_models):

    gender_queries, negative_test_queries, models = queries_and_models
    results_gender = run_queries(WEAT, gender_queries, models,
                                 queries_set_name='Gender Queries',
                                 include_average_by_embedding='include')
    results_test = run_queries(WEAT, negative_test_queries, models,
                               queries_set_name='Negative Test Queries',
                               include_average_by_embedding='include')

    ranking = create_ranking([results_gender, results_test])

    correlations = calculate_ranking_correlations(ranking)

    assert correlations.shape == (2, 2)
    assert np.array_equal(
        correlations.columns.values,
        np.array([
            'WEAT: Gender Queries average score',
            'WEAT: Negative Test Queries average score'
        ]))
    assert np.array_equal(
        correlations.index.values,
        np.array([
            'WEAT: Gender Queries average score',
            'WEAT: Negative Test Queries average score'
        ]))