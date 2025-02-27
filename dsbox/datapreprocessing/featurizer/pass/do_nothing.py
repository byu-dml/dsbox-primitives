from d3m.container.pandas import DataFrame
from d3m.primitive_interfaces.base import CallResult
from d3m.primitive_interfaces.transformer import TransformerPrimitiveBase
from d3m.metadata import hyperparams
from . import config

Inputs = DataFrame
Outputs = DataFrame


class DoNothingHyperparams(hyperparams.Hyperparams):
    pass


class DoNothing(TransformerPrimitiveBase[Inputs, Outputs, DoNothingHyperparams]):
    '''
    A primitive which only pass the input to the output
    '''
    __author__ = 'USC ISI'
    metadata = hyperparams.base.PrimitiveMetadata({
        'id': 'dsbox-featurizer-do-nothing',
        'version': config.VERSION,
        'name': 'DSBox do-nothing primitive',
        'description': 'Just pass the input to the output',
        'python_path': 'd3m.primitives.data_preprocessing.do_nothing.DSBOX',
        'primitive_family': 'DATA_PREPROCESSING',
        'algorithm_types': ["NUMERICAL_METHOD"],
        'keywords': ['pass'],
        'source': {
            'name': config.D3M_PERFORMER_TEAM,
            "contact": config.D3M_CONTACT,
            'uris': [config.REPOSITORY]
            },
        'installation': [config.INSTALLATION],
        # Choose these from a controlled vocabulary in the schema. If anything is missing which would
        # best describe the primitive, make a merge request.

        # A metafeature about preconditions required for this primitive to operate well.
        'precondition': [],
        'hyperparms_to_tune': []
    })

    def __init__(self, *, hyperparams: DoNothingHyperparams) -> None:
        super().__init__(hyperparams=hyperparams)
        self.hyperparams = hyperparams
        # All other attributes must be private with leading underscore
        self._has_finished = False
        self._iterations_done = False

    def produce(self, *, inputs: Inputs, timeout: float = None, iterations: int = None) -> CallResult[Outputs]:

        self._has_finished = True
        self._iterations_done = True
        return CallResult(inputs, self._has_finished, self._iterations_done)
