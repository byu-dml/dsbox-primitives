import logging
import re
import time

import stopit  # type: ignore
import pandas as pd

from d3m.primitive_interfaces.featurization import FeaturizationTransformerPrimitiveBase
from d3m.primitive_interfaces.base import CallResult
from d3m.metadata import hyperparams
from d3m import container
from d3m.metadata import base as metadata_base

from .helper import Aggregator
from . import config

Inputs = container.Dataset
Outputs = container.DataFrame

_logger = logging.getLogger(__name__)


class MultiTableFeaturizationHyperparams(hyperparams.Hyperparams):
    VERBOSE = hyperparams.Hyperparameter[bool](
        default=False,
        semantic_types=['https://metadata.datadrivendiscovery.org/types/ControlParameter'],
        description="Display the track of detail processing steps or not",
    )


class MultiTableFeaturization(FeaturizationTransformerPrimitiveBase[Inputs, Outputs, MultiTableFeaturizationHyperparams]):
    """
    Generate a featurized table from multiple-table dataset using aggregation. It will automatically detect foriegn key
    relationships among multiple tables, and join the tables into one table using aggregation.
    """
    __author__ = 'USC ISI'
    metadata = hyperparams.base.PrimitiveMetadata({
        'id': 'dsbox-multi-table-featurization-aggregation',
        'version': config.VERSION,
        'name': "DSBox Multiple Table Featurizer Aggregation",
        'python_path': 'd3m.primitives.feature_extraction.multitable_featurization.DSBOX',
        'primitive_family': "FEATURE_EXTRACTION",
        'algorithm_types': ["RELATIONAL_DATA_MINING"],
        'keywords': ['multiple table'],
        'source': {
            'name': config.D3M_PERFORMER_TEAM,
            "contact": config.D3M_CONTACT,
            'uris': [config.REPOSITORY]
            },
            # The same path the primitive is registered with entry points in setup.py.
        'installation': [config.INSTALLATION],
        # Choose these from a controlled vocabulary in the schema. If anything is missing which would
        # best describe the primitive, make a merge request.

        # A metafeature about preconditions required for this primitive to operate well.
        'precondition': [],
        'hyperparms_to_tune': []
    })

    def __init__(self, *, hyperparams: MultiTableFeaturizationHyperparams) -> None:

        super().__init__(hyperparams=hyperparams)
        self.hyperparams = hyperparams

        # All other attributes must be private with leading underscore
        self._has_finished = False
        self._iterations_done = False
        self._verbose = self.hyperparams['VERBOSE']

    def produce(self, *, inputs: Inputs, timeout: float = None, iterations: int = None) -> CallResult[Outputs]:

        if (timeout is None):
            big_table = self._core(inputs)
            self._has_finished = True
            self._iterations_done = True
            return CallResult(big_table, self._has_finished, self._iterations_done)
        else:
            # setup the timeout
            with stopit.ThreadingTimeout(timeout) as to_ctx_mrg:
                assert to_ctx_mrg.state == to_ctx_mrg.EXECUTING

                # core computations
                big_table = self._core(inputs)

            if to_ctx_mrg.state == to_ctx_mrg.EXECUTED:
                self._has_finished = True
                self._iterations_done = True
                return CallResult(big_table, self._has_finished, self._iterations_done)
            elif to_ctx_mrg.state == to_ctx_mrg.TIMED_OUT:
                self._has_finished = False
                self._iterations_done = False
                return CallResult(None, self._has_finished, self._iterations_done)

    def _core(self, inputs: Inputs) -> Outputs:
        """
        core calculations
        """
        data = inputs.copy()
        relations = []
        # step 1: Generate the relation sets
        # search in each dataset and find the foreign key relationship
        all_metadata = {}
        for resource_id in data.keys():
            # get relationship of foreign keys
            columns_length = inputs.metadata.query((resource_id, metadata_base.ALL_ELEMENTS))['dimension']['length']
            for column_index in range(columns_length):
                column_metadata = inputs.metadata.query((resource_id, metadata_base.ALL_ELEMENTS, column_index))
                # save each column's metadata for further adding back
                resource_column_name = resource_id + "_" + data[resource_id].columns[column_index]
                all_metadata[resource_column_name] = column_metadata
                # find the main resource id
                if 'https://metadata.datadrivendiscovery.org/types/SuggestedTarget' in column_metadata['semantic_types']:
                    main_resource_id = resource_id
                    _logger.debug("Main table ID is: %s", main_resource_id)
                    if self._verbose:
                        _logger.info("Main table ID is:", main_resource_id)
                # find the foreign key relationship
                if 'foreign_key' in column_metadata:
                    ref_resource_id = column_metadata['foreign_key']['resource_id']
                    if "https://metadata.datadrivendiscovery.org/types/FilesCollection" in inputs.metadata.query((ref_resource_id,))['semantic_types']:
                        _logger.debug('Skipping file collection resource id=%s', ref_resource_id)
                        continue
                    # Can reference by name or by column
                    if 'column_name' in column_metadata['foreign_key']:
                        foreign_column_name = column_metadata['foreign_key']['column_name']
                    else:
                        foreign_column_index = column_metadata['foreign_key']['column_index']
                        foreign_column_name = inputs.metadata.query(
                            (column_metadata['foreign_key']['resource_id'],
                             metadata_base.ALL_ELEMENTS,
                             foreign_column_index))['name']
                    target_column_name = column_metadata['foreign_key']['resource_id'] + "_" + foreign_column_name
                    column_metadata['foreign_key']
                    # generate a set with format (target_id+target_column_index, resource_id+resource_column_index)
                    each_relation = (target_column_name, resource_column_name)
                    relations.append(each_relation)

        # if no foreign key relationships found, return inputs directly
        if len(relations) == 0:
            _logger.info("No table-based foreign_key relationship found in the dataset, will return the original dataset.")
            _logger.info("[INFO] No table-based foreign_key relationship found in the dataset, will return the original dataset.")
            return inputs

        # step 2.5: a fix (based on the problem occurred in `uu3_world_development_indicators` dataset)
        if _logger.getEffectiveLevel() <= 10:
            _logger.debug('Relations')
            for target_column_name, resource_column_name in relations:
                _logger.debug('  Target_column=%s Resource_column=%s', target_column_name, resource_column_name)
        relations = self._relations_correction(relations=relations)
        if self._verbose:
            _logger.info("==========relations:=============")
            _logger.info(relations) # to see if the relations make sense
            _logger.info("=================================")
        if _logger.getEffectiveLevel() <= 10:
            _logger.debug('Corrected Relations')
            for target_column_name, resource_column_name in relations:
                _logger.debug('  Target_column=%s Resource_column=%s', target_column_name, resource_column_name)

        # step 3: featurization
        start = time.clock()
        _logger.info("[INFO] Multi-table join start.")
        aggregator = Aggregator(relations, data, self._verbose)
        for each_relation in relations:
            # if the target table found in second placfe of the set
            if main_resource_id in each_relation[1]:
                big_table = aggregator.backward_new(each_relation[1])
                break
            # if the target table found in first placfe of the set
            if main_resource_id in each_relation[0]:
                big_table = aggregator.forward(each_relation[0])
                break
        finish = time.clock()
        _logger.info("[INFO] Multi-table join finished, totally take ", finish-start, 'seconds.')
        big_table = container.DataFrame(pd.DataFrame(big_table), generate_metadata=True)
        # add back metadata
        for index in range(len(big_table.columns)):
            old_metadata = all_metadata[big_table.columns[index]]
            big_table.metadata = big_table.metadata.update((metadata_base.ALL_ELEMENTS, index), old_metadata)

        # import pdb
        # pdb.set_trace()
        return big_table

    def _relations_correction(self, relations):
        """
        to correct the obtained relations:
            1. if more than one relation found btw. two tables, only pick one of them
        """
        # using easist way to fix: a set that avoid duplicates
        table_tuple_set = set() # store the set of tuples of tables: {(table1, table2), (table1, table3), ...}
        relations_corrected = set()

        for foreign_key, primary_key in relations:
            foreign_table = re.split('_', foreign_key)[0]
            primary_table = re.split('_', primary_key)[0]
            table_tuple = (foreign_table, primary_table)
            if (table_tuple in table_tuple_set):
                continue
            else:
                table_tuple_set.add(table_tuple)
                relations_corrected.add((foreign_key, primary_key))

        return relations_corrected
