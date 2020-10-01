# Visualization functions for our trees
#
# Copyright 2020 Yuriy Sverchkov
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pkgutil
import json
from logging import getLogger
from generalizedtrees.queues import Stack
import generalizedtrees.constraints as cons

logger = getLogger()

DATA_TEMPLATE_STR = '/***DATA***/'
ARTIST_TEMPLATE_STR = '/**DRAWING SCRIPT**/'

def _load_html_template():
    return pkgutil.get_data('generalizedtrees.vis', 'template.html').decode('utf-8')

def _load_dt_js():
    return pkgutil.get_data('generalizedtrees.vis', 'decision_tree.js').decode('utf-8')

def explanation_to_html(explanation, out_file, feature_annotations = None):

    json_str = explanation_to_JSON(explanation, feature_annotations)
    # We anticipate possibly using different templates depending on model type
    html_template = _load_html_template()
    dt_artist = _load_dt_js()

    if hasattr(out_file, 'write'):
        _frankenstein(json_str, dt_artist, html_template, out_file)
    else:
        with open(out_file, 'wt') as f:
            _frankenstein(json_str, dt_artist, html_template, f)

def _frankenstein(data_str, artist_str, template_str, out_file):
    
    out_file.write(template_str
        .replace(DATA_TEMPLATE_STR, 'data = ' + data_str + ';')
        .replace(ARTIST_TEMPLATE_STR, artist_str))


def _get_constraint_type_as_html_string(constraint):
    if isinstance(constraint, cons.GTConstraint):
        return f'> {constraint.value:.4g}'
    if isinstance(constraint, cons.LEQConstraint):
        return f'\u2264 {constraint.value:.4g}'
    if isinstance(constraint, cons.EQConstraint):
        return f'= {constraint.value:.4g}'
    if isinstance(constraint, cons.NEQConstraint):
        return f'\u2260 {constraint.value:.4g}'
    # Fall through catch-all
    return str(constraint)


def explanation_to_JSON(explanation, feature_annotations = None):

    root = dict()

    stack = Stack()
    stack.push((root, explanation.tree.node('root')))

    while (stack):

        out_node, in_node = stack.pop()

        # Record training set counts (and target distributions)
        if hasattr(in_node.item, 'training_target_proba'):
            if 'samples' not in out_node:
                out_node['samples'] = dict()
            out_node['samples'].update({f'training_labeled_{k}': v for k, v in
                in_node.item.training_target_proba.sum(axis=0).iteritems()})

        # Record training set counts (and target distributions)
        if hasattr(in_node.item, 'gen_target_proba'):
            if 'samples' not in out_node:
                out_node['samples'] = dict()
            out_node['samples'].update({f'generated_labeled_{k}': v for k, v in
                in_node.item.gen_target_proba.sum(axis=0).iteritems()})

        # Record split
        if hasattr(in_node.item, 'split') and in_node.item.split is not None:
            out_node['split'] = str(in_node.item.split)

            if feature_annotations is not None:
                try:
                    f = in_node.item.split.feature
                    annotation = feature_annotations.loc[f]
                    out_node['feature_annotation'] = [{'annotation': 'feature id', 'value': f}]
                    out_node['feature_annotation'].extend([
                        {'annotation': i, 'value': v} for i, v in annotation.iteritems()])
                
                except Exception as e:
                    logger.warning(
                        f"Could not bind feature annotation to {in_node.item.split}",
                        exc_info=e)
        
        # Record children
        if not in_node.is_leaf:
            out_node['children'] = [
                {'branch': _get_constraint_type_as_html_string(c.item.local_constraint)}
                for c in in_node]
            for pair in zip(out_node['children'], in_node):
                stack.push(pair)
        
        # Node-model specific conversions
        # should it be the node class' responsibility to implement these?
        if hasattr(in_node.item, 'probabilities'):
            out_node['probabilities'] = [{'value': x} for x in in_node.item.probabilities]
            if hasattr(in_node.item.probabilities, 'index'):
                for d, i in zip(out_node['probabilities'], in_node.item.probabilities.index):
                    d['target'] = i
        
        if hasattr(in_node.item, 'model'):
            model = in_node.item.model
            # Monkey check for LR/linear model
            # TODO: Handle case when intercept+coef are multi-d
            if hasattr(model, 'coef_') and hasattr(model, 'intercept_'):
                if hasattr(model.intercept_, 'shape'):
                    intercept = model.intercept_.flat[0]
                else:
                    intercept = model.intercept_
                out_node['logistic_model'] = [{'label': 'intercept', 'value': intercept}]
                try:
                    coefficients = [{'label': key, 'value': value}
                        for (key, value) in zip(explanation.feature_names, model.coef_.flat)
                        if abs(value) > 0]
                except:
                    logger.critical(
                        'Could not convert logistic model to JSON:'
                        f'\ncoef_: {model.coef_}')
                    raise
                out_node['logistic_model'].extend(coefficients)
    
    return json.dumps(root)
