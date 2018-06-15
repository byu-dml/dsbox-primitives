#!/usr/bin/env python3

import argparse
import os.path
import subprocess
from dsbox.datapreprocessing.featurizer import config as featurizer_config

parser = argparse.ArgumentParser(description='Generate primitive.json descriptions')
parser.add_argument(
    'dirname', action='store', help='Top-level directory to store the json descriptions, i.e. primitives_repo directory')
arguments = parser.parse_args()


PREFIX = 'd3m.primitives.dsbox.'
PRIMITIVES = [
    ('ResNet50ImageFeature', featurizer_config),
    ('Vgg16ImageFeature', featurizer_config),
    ('MultiTableFeaturization', featurizer_config),
    ('DataFrameToTensor', featurizer_config),
]

for p, config in PRIMITIVES:
    print('Generating json for primitive ' + p)
    primitive_name = PREFIX + p
    outdir = os.path.join(arguments.dirname, 'v'+config.D3M_API_VERSION,
                       config.D3M_PERFORMER_TEAM, primitive_name,
                       config.VERSION)
    subprocess.run(['mkdir', '-p', outdir])

    json_filename =  os.path.join(outdir, 'primitive.json')
    print('    at ' + json_filename)
    command = ['python', '-m', 'd3m.index', 'describe', '-i', '4', primitive_name]
    with open(json_filename, 'w') as out:
        subprocess.run(command, stdout=out)
