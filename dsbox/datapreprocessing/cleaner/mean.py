import numpy as np
import pandas as pd
from fancyimpute import SimpleFill

from . import missing_value_pred as mvp
from primitive_interfaces.unsupervised_learning import UnsupervisedLearnerPrimitiveBase

from primitive_interfaces.base import CallMetadata
from typing import NamedTuple, Sequence
import stopit
import math

from d3m_metadata.container import DataFrame

Input = DataFrame
Output = DataFrame
Hyperparameter = None

# store the mean value for each column in training data
Params = NamedTuple("params", [
    ('mean_values', dict)]
    ) 

class MeanImputation(UnsupervisedLearnerPrimitiveBase[Input, Output, Params, Hyperparameter]):
    __author__ = "USC ISI"
    __metadata__ = {
        "id": "7894b699-61e9-3a50-ac9f-9bc510466667",
        "name": "dsbox.datapreprocessing.cleaner.MeanImputation",
        "common_name": "DSBox Mean Imputer",
        "description": "Impute missing values using mean",
        "languages": [
            "python3.5", "python3.6"
        ],
        "library": "dsbox",
        "version": "0.2.0",
        "is_class": True,
        "parameters": [],
        "task_type": [
            "Data preprocessing"
        ],
        "tags": [
            "preprocessing",
            "imputation"
        ],
        "build": [
            {
                "type": "pip",
                "package": "dsbox-datacleaning"
            }
        ],
        "team": "USC ISI",
        "schema_version": 1.0,
        "interfaces": [ "UnsupervisedLearnerPrimitiveBase" ],
        "interfaces_version": "2017.9.22rc0",
        "compute_resources": {
            "cores_per_node": [],
            "disk_per_node": [],
            "expected_running_time": [],
            "gpus_per_node": [],
            "mem_per_gpu": [],
            "mem_per_node": [],
            "num_nodes": [],
            "sample_size": [],
            "sample_unit": []
        }
    }

    """
    Imputate the missing value using the `mean` value of the attribute
    """

    def __init__(self, verbose=0) -> None:
        self.train_x = None
        self._has_finished = False
        self._iterations_done = False
        self.verbose = verbose

    def set_params(self, *, params: Params) -> None:
        self.is_fitted = len(params.mean_values) > 0
        self._has_finished = self.is_fitted
        self.mean_values = params.mean_values

    def get_params(self) -> Params:
        if self.is_fitted:
            return Params(mean_values=self.mean_values)
        else:
            return Params(mean_values=dict)   

    def set_training_data(self, *, inputs: Sequence[Input]) -> None:
        """
        Sets training data of this primitive.

        Parameters
        ----------
        inputs : Sequence[Input]
            The inputs.
        """
        if (pd.isnull(inputs).sum().sum() == 0):    # no missing value exists
            self.is_fitted = True
            if (self.verbose > 0): print ("Warning: no missing value in train dataset")
        else:
            self.train_x = inputs
            self.is_fitted = False


    def get_call_metadata(self) -> CallMetadata:
            return CallMetadata(has_finished=self._has_finished, iterations_done=self._iterations_done)


    def fit(self, *, timeout: float = None, iterations: int = None) -> None:
        """
        get the mean value of each columns

        Parameters:
        ----------
        data: pandas dataframe
        """

        # if already fitted on current dataset, do nothing
        if self.is_fitted:
            return True

        if (timeout is None):
            timeout = math.inf
        if (iterations is None):
            self._iterations_done = True

        # setup the timeout
        with stopit.ThreadingTimeout(timeout) as to_ctx_mrg:
            assert to_ctx_mrg.state == to_ctx_mrg.EXECUTING

            # start fitting
            if (self.verbose>0) : print("=========> mean imputation method:")
            self.__get_fitted()

        if to_ctx_mrg.state == to_ctx_mrg.EXECUTED:
            self.is_fitted = True
            self._iterations_done = True
            self._has_finished = True
        elif to_ctx_mrg.state == to_ctx_mrg.TIMED_OUT:
            self.is_fitted = False
            self._iterations_done = False
            self._has_finished = False
            return

    def produce(self, *, inputs: Sequence[Input], timeout: float = None, iterations: int = None) -> Sequence[Output]:
        """
        precond: run fit() before

        Parameters:
        ----------
        data: pandas dataframe
        """

        if (not self.is_fitted):
            # todo: specify a NotFittedError, like in sklearn
            raise ValueError("Calling produce before fitting.")
        if (pd.isnull(inputs).sum().sum() == 0):    # no missing value exists
            if (self.verbose > 0): print ("Warning: no missing value in test dataset")
            self._has_finished = True
            return inputs

        if (timeout is None):
            timeout = math.inf

        if isinstance(inputs, pd.DataFrame):
            data = inputs.copy()
        else:
            data = inputs[0].copy()

        # setup the timeout
        with stopit.ThreadingTimeout(timeout) as to_ctx_mrg:
            assert to_ctx_mrg.state == to_ctx_mrg.EXECUTING

            # start completing data...
            if (self.verbose>0): print("=========> impute by mean value of the attribute:")

            # assume the features of testing data are same with the training data
            # therefore, only use the mean_values to impute, should get a clean dataset
            data_clean = data.fillna(value=self.mean_values)


        if to_ctx_mrg.state == to_ctx_mrg.EXECUTED:
            self._has_finished = True
            self._iterations_done = True
            return data_clean
        elif to_ctx_mrg.state == to_ctx_mrg.TIMED_OUT:
            self._has_finished = False
            self._iterations_done = False
            return None


    def __get_fitted(self):
        self.mean_values = self.train_x.mean(axis=0).to_dict()


