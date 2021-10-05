# Tests for born-again trees
#
# Licensed under the BSD 3-Clause License
# Copyright (c) 2020, Yuriy Sverchkov

def test_bat(breast_cancer_data_pandas, breast_cancer_rf_model, caplog):

    from generalizedtrees.recipes import born_again_tree
    from time import perf_counter
    import logging

    logger = logging.getLogger()
    caplog.set_level(logging.DEBUG)

    x_train = breast_cancer_data_pandas.x_train
    x_test = breast_cancer_data_pandas.x_test
    model = breast_cancer_rf_model
    
    # Verify output shape of model
    logger.debug(f'Model probability prediction:\n{model.predict_proba(x_test)}')   

    # Learn explanation
    t1 = perf_counter()

    logger.info('Creating class instance')
    explain = born_again_tree(max_tree_size=5, max_attempts=4)

    logger.info('Fitting tree')
    oracle = model.predict_proba
    tree = explain.fit(x_train, oracle)

    t2 = perf_counter()

    logger.info(f'Time taken: {t2-t1}')

    logger.info(f'Learned tree:\n{tree.show()}')

    # Make predictions
    logger.info('Running prediction')
    explainer_predictions = tree.predict(x_test)

    logger.info(f'Predictions: {list(explainer_predictions)}')

    logger.info("Done")