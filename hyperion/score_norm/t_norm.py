"""
 Copyright 2018 Johns Hopkins University  (Author: Jesus Villalba)
 Apache 2.0  (http://www.apache.org/licenses/LICENSE-2.0)
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from six.moves import xrange

import numpy as np
import h5py

from .score_norm import ScoreNorm

class TNorm(ScoreNorm):
    """Class for T-Norm score normalization.
    """
    def predict(self, scores, scores_coh_test, mask=None):

        if mask is None:
            mu_t = np.mean(scores_coh_test, axis=0, keepdims=True)
            s_t = np.std(scores_coh_test, axis=0, keepdims=True)
        else:
            scores_coh_test[mask==False] = 0
            n_t = np.mean(mask, axis=0, keepdims=True)
            mu_t = np.mean(scores_coh_test, axis=0, keepdims=True)/n_t
            s_t = np.sqrt(np.mean(scores_coh_test**2, axis=0, keepdims=True)/n_t - mu_t**2)
            
        s_t[s_t<self.std_floor] = self.std_floor
        
        scores_norm = (scores - mu_t)/s_t
        return scores_norm
