import numpy as np
import pandas as pd
from fancyimpute import KNN as knn

from . import missing_value_pred as mvp
from primitive_interfaces.transformer import TransformerPrimitiveBase
from primitive_interfaces.base import CallMetadata
from typing import NamedTuple, Sequence
import stopit
import math

Input = pd.DataFrame
Output = pd.DataFrame


class KNNImputation(TransformerPrimitiveBase[Input, Output]):
    __author__ = "USC ISI"
    __metadata__ = {
        "id": "faeeb725-6546-3f55-b80d-8b79d5ca270a",
        "name": "dsbox.datapreprocessing.cleaner.KNNImputation",
        "common_name": "DSBox KNN Imputer",
        "description": "Impute missing values using k-nearest neighbor",
        "languages": [
            "python3.5",
            "python3.6"
        ],
        "library": "dsbox",
        "version": "0.2.0",
        "is_class": true,
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
        "interfaces": [
            "TransformerPrimitiveBase"
        ],
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
    Impute the missing value using k nearest neighbors (weighted average). 
    This class is a wrapper from fancyimpute-knn

    Parameters:
    ----------
    k: the number of nearest neighbors

    verbose: Integer
        Control the verbosity

    """

    def __init__(self, verbose=0) -> None:
        self.train_x = None
        self._has_finished = False
        self._iterations_done = False
        self.k = 5
        self.verbose = verbose


    def get_call_metadata(self) -> CallMetadata:
            return CallMetadata(has_finished=self._has_finished, iterations_done=self._iterations_done)


    def produce(self, *, inputs: Sequence[Input], timeout: float = None, iterations: int = None) -> Sequence[Output]:
        """
        precond: run fit() before

        to complete the data, based on the learned parameters, support:
        -> greedy search

        also support the untrainable methods:
        -> iteratively regression
        -> other

        Parameters:
        ----------
        data: pandas dataframe
        label: pandas series, used for the evaluation of imputation

        TODO:
        ----------
        1. add evaluation part for __simpleImpute()

        """

        if (timeout is None):
            timeout = math.inf

        if isinstance(inputs, pd.DataFrame):
            data = inputs.copy()
        else:
            data = inputs[0].copy()
        # record keys:
        keys = data.keys()
        index = data.index

        # setup the timeout
        with stopit.ThreadingTimeout(timeout) as to_ctx_mrg:
            assert to_ctx_mrg.state == to_ctx_mrg.EXECUTING

            # start completing data...
            if (self.verbose>0): print("=========> impute by fancyimpute-knn:")
            data_clean = self.__knn(data)


        if to_ctx_mrg.state == to_ctx_mrg.EXECUTED:
            self._has_finished = True
            self._iterations_done = True
            return pd.DataFrame(data_clean, index, keys)
        elif to_ctx_mrg.state == to_ctx_mrg.TIMED_OUT:
            self._has_finished = False
            self._iterations_done = False
            return None


    #============================================ core function ============================================
    def __knn(self, test_data):
        """
        wrap fancyimpute-knn
        """
        missing_col_id = []
        test_data = mvp.df2np(test_data, missing_col_id, self.verbose)
        if (len(missing_col_id) == 0): return test_data
        complete_data = knn(k=self.k, verbose=self.verbose).complete(test_data)
        return complete_data

