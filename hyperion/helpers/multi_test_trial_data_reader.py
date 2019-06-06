"""
 Copyright 2018 Johns Hopkins University  (Author: Jesus Villalba)
 Apache 2.0  (http://www.apache.org/licenses/LICENSE-2.0)
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from six.moves import xrange

import sys
import os
import argparse
import time
import copy

import numpy as np

from ..io import RandomAccessDataReaderFactory as DRF
from ..utils.utt2info import Utt2Info
from ..utils.trial_ndx import TrialNdx
from ..transforms import TransformList

class MultiTestTrialDataReader(object):
    """
    Loads Ndx, enroll file and x-vectors to evaluate PLDA.
    """

    def __init__(self, v_file, ndx_file, enroll_file, test_file, test_utt2orig_file,
                 preproc, tlist_sep=' ', 
                 model_idx=1, num_model_parts=1, seg_idx=1, num_seg_parts=1,
                 eval_set='enroll-test'):

        self.r = DRF.create(v_file)
        self.preproc = preproc

        enroll = Utt2Info.load(enroll_file, sep=tlist_sep)
        test = None
        if test_file is not None:
            test = Utt2Info.load(test_file, sep=tlist_sep)
        ndx = None
        if ndx_file is not None:
            ndx = TrialNdx.load(ndx_file)

        utt2orig = Utt2Info.load(test_utt2orig_file, sep=tlist_sep)
                
        ndx, enroll = TrialNdx.parse_eval_set(ndx, enroll, test, eval_set)
        if num_model_parts > 1 or num_seg_parts > 1:
            ndx = TrialNdx.split(model_idx, num_model_parts, seg_idx, num_seg_parts)
            enroll = enroll.filter_info(ndx.model_set)
            utt2orig =utt2orig.filter_info(ndx.seg_set)

        self.enroll = enroll
        self.ndx = ndx
        self.utt2orig = utt2orig

        
    def read(self):
        x_e = self.r.read(self.enroll.key, squeeze=True)
        x_t = self.r.read(self.utt2orig.key, squeeze=True)
    
        if self.preproc is not None:
            x_e = self.preproc.predict(x_e)
            x_t = self.preproc.predict(x_t)

        return x_e, x_t, self.enroll.info, self.ndx, self.utt2orig.info



    @staticmethod
    def filter_args(prefix=None, **kwargs):
        if prefix is None:
            p = ''
        else:
            p = prefix + '_'
        valid_args = ('tlist_sep', 
                      'model_idx','num_model_parts',
                      'seg_idx', 'num_seg_parts',
                      'eval_set')
        return dict((k, kwargs[p+k])
                    for k in valid_args if p+k in kwargs)

    
    @staticmethod
    def add_argparse_args(parser, prefix=None):
        if prefix is None:
            p1 = '--'
            p2 = ''
        else:
            p1 = '--' + prefix + '-'
            p2 = prefix + '_'
        parser.add_argument(p1+'tlist-sep', dest=(p2+'tlist_sep'), default=' ',
                            help=('trial lists field separator'))
        # parser.add_argument(p1+'v-field', dest=(p2+'v_field'), default='',
        #                     help=('dataset field in the data file'))

        parser.add_argument(p1+'model-part-idx', dest=(p2+'model_idx'), default=1, type=int,
                            help=('model part index'))
        parser.add_argument(p1+'num-model-parts', dest=(p2+'num_model_parts'), default=1, type=int,
                            help=('number of parts in which we divide the model'
                                  'list to run evaluation in parallel'))
        parser.add_argument(p1+'seg-part-idx', dest=(p2+'seg_idx'), default=1, type=int,
                            help=('test part index'))
        parser.add_argument(p1+'num-seg-parts', dest=(p2+'num_seg_parts'), default=1, type=int,
                            help=('number of parts in which we divide the test list '
                                  'to run evaluation in parallel'))
        
        parser.add_argument(p1+'eval-set', dest=(p2+'eval_set'), type=str.lower,
                            default='enroll-test',
                            choices=['enroll-test','enroll-coh','coh-test','coh-coh'],
                            help=('evaluation subset'))
