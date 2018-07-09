import pandas as pd
import numpy as np
from numpy import ndarray
import typing
from typing import Any, Callable, List, Dict, Union, Optional, Sequence, Tuple
from d3m import container
import d3m.metadata.base as mbase
from . import config
from d3m.primitive_interfaces.featurization import FeaturizationLearnerPrimitiveBase
from common_primitives import utils
from d3m.metadata import hyperparams, params
from d3m.container import DataFrame as d3m_DataFrame
from d3m.primitive_interfaces.base import CallResult
from sklearn.preprocessing import LabelEncoder
from collections import defaultdict

__all__ = ('Labler',)

Inputs = container.DataFrame
Outputs = container.DataFrame

class Params(params.Params):
    labler_dict: Dict
    s_cols: List[object]

class LablerHyperparams(hyperparams.Hyperparams):
    pass

class Labler(FeaturizationLearnerPrimitiveBase[Inputs, Outputs, Params, LablerHyperparams]):
    """
        A primitive which scales all the Integer & Float variables in the Dataframe.
    """
    __author__ = 'USC ISI'
    metadata = hyperparams.base.PrimitiveMetadata({
        "id": "dsbox-multi-table-feature-labler",
        "version": config.VERSION,
        "name": "DSBox feature labeler",
        "description": "A simple primitive that labels all string based categorical columns",
        "python_path": "d3m.primitives.dsbox.Labler",
        "primitive_family": "DATA_CLEANING",
        "algorithm_types": ["DATA_NORMALIZATION"],
        "source": {
            "name": config.D3M_PERFORMER_TEAM,
            "uris": [config.REPOSITORY]
        },
        "keywords": ["NORMALIZATION", "Labler"],
        "installation": [config.INSTALLATION],
        "precondition": ["NO_MISSING_VALUES", "CATEGORICAL_VALUES"],

    })

    def __init__(self, *, hyperparams: LablerHyperparams) -> None:
        super().__init__(hyperparams=hyperparams)
        self.hyperparams = hyperparams
        self._training_data = None
        self._fitted = False
        self._s_cols = None
        self._model = defaultdict(LabelEncoder)
        self._has_finished = False
        self._iterations_done = False

    def set_training_data(self, *, inputs: Inputs) -> None:
        self._training_data = inputs

    def fit(self, *, timeout: float = None, iterations: int = None) -> CallResult[None]:
        import pdb
        pdb.set_trace()
        categorical_attributes = utils.list_columns_with_semantic_types(
            metadata=self._training_data.metadata,
            semantic_types=[
                "https://metadata.datadrivendiscovery.org/types/OrdinalData",
                "https://metadata.datadrivendiscovery.org/types/CategoricalData"
                ]
            )

        all_attributes = utils.list_columns_with_semantic_types(
            metadata=self._training_data.metadata,
            semantic_types=["https://metadata.datadrivendiscovery.org/types/Attribute"]
            )

        self._s_cols = container.List(set(all_attributes).intersection(categorical_attributes))
        print("[INFO] %d of categorical attributes found." % (len(self._s_cols)))

        if len(self._s_cols) > 0:
            self._training_data.iloc[:,self._s_cols].apply(lambda x: self._model[x.name].fit(x))
            self._fitted = True
        else:
            self._fitted = False

    def produce(self, *, inputs: Inputs, timeout: float = None, iterations: int = None) -> CallResult[Outputs]:
        if not self._fitted:
            return CallResult(inputs, self._has_finished, self._iterations_done)

        temp = pd.DataFrame(inputs.iloc[:, self._s_cols].apply(lambda x: self._model[x.name].transform(x)))
        outputs = inputs.copy()
        for id_index, od_index in zip(self._s_cols, range(temp.shape[1])):
            outputs.iloc[:, id_index] = temp.iloc[:, od_index]
        lookup = {"int": ('http://schema.org/Integer', 'https://metadata.datadrivendiscovery.org/types/Attribute')}

        for index in self._s_cols:
            old_metadata = dict(outputs.metadata.query((mbase.ALL_ELEMENTS, index)))
            old_metadata["semantic_types"] = lookup["int"]
            old_metadata["structural_type"] = type(10)
            outputs.metadata = outputs.metadata.update((mbase.ALL_ELEMENTS, index), old_metadata)

        if outputs.shape == inputs.shape:
            self._has_finished = True
            self._iterations_done = True
            print("output:",outputs.head(5))
            return CallResult(d3m_DataFrame(outputs), self._has_finished, self._iterations_done)
        else:
            return CallResult(inputs, self._has_finished, self._iterations_done)

    def get_params(self) -> Params:
        labeler_dict = {}
        if self._model:
            # extract the dictionary of the models
            for each_key,each_value in self._model.items():
                labeler_dict[each_key] = each_value.classes_
            # return parameters
            return Params(s_cols = self._s_cols,
                          labler_dict = labeler_dict
                        )
        else:
            return Params({
                's_cols':[],
                'labler_dict':{} 
                })

    def set_params(self, *, params: Params) -> None:
        self._s_cols = params['s_cols']
        if params['labler_dict']:
            self._model = defaultdict(LabelEncoder)
            for each_key, each_value in params['labler_dict'].items():
                each_encoder = LabelEncoder()
                each_encoder.classes_ = each_value
                self._model[each_key] = each_encoder
            self._fitted = True
        else:
            self._fitted = False
