"""
 Copyright 2019 Johns Hopkins University  (Author: Jesus Villalba)
 Apache 2.0  (http://www.apache.org/licenses/LICENSE-2.0)
"""
from __future__ import absolute_import
from __future__ import print_function

import torch

class Reshape(object):

    def __init__(self, shape):
        self.shape = shape

    def __call__(self, x):
        return torch.reshape(x, shape=self.shape)

    
