#!/usr/bin/env python
"""
 Copyright 2018 Johns Hopkins University  (Author: Jesus Villalba)
 Apache 2.0  (http://www.apache.org/licenses/LICENSE-2.0)
"""
"""
Trains x-vector with LDE
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from six.moves import xrange

import sys
import os
import argparse
import time
import logging

import numpy as np

from hyperion.hyp_defs import set_float_cpu, float_cpu, config_logger
from hyperion.utils.multithreading import threadsafe_generator
from hyperion.generators import SequenceBatchGeneratorV1 as G
from hyperion.transforms import TransformList
from hyperion.keras.backend_addons import reserve_gpu
from hyperion.keras.keras_utils import *
from hyperion.keras.keras_model_loader import KerasModelLoader as KML
from hyperion.keras.helpers import OptimizerFactory as KOF
from hyperion.keras.helpers import CallbacksFactory as KCF
from hyperion.keras.embed import SeqEmbedLDE as SeqEmbed



@threadsafe_generator
def data_generator(sg, max_length):

    while 1:
        key, x, sample_weight, y = sg.read(max_seq_length=max_length)
        yield (x, y)
        

    
def train_embed(data_path, train_list, val_list,
                prepool_net_path, postpool_net_path, loss,
                init_path, epochs, 
                preproc_file, output_path,
                freeze_prepool, freeze_prepool_layers, freeze_postpool_layers,
                **kwargs):
    
    g = reserve_gpu()
    set_float_cpu(float_keras())
        
    if init_path is None:
        model, init_epoch = KML.load_checkpoint(output_path, epochs)
        if model is None:
            emb_args = SeqEmbed.filter_args(**kwargs)
            prepool_net = load_model_arch(prepool_net_path)
            postpool_net = load_model_arch(postpool_net_path)

            model = SeqEmbed(prepool_net, postpool_net,
                             loss=loss,
                             **emb_args)
        else:
            kwargs['init_epoch'] = init_epoch
    else:
        logging.info('loading init model: %s' % init_path)
        model = KML.load(init_path)

    
    sg_args = G.filter_args(**kwargs)
    opt_args = KOF.filter_args(**kwargs)
    cb_args = KCF.filter_args(**kwargs)
    logging.debug(sg_args)
    logging.debug(opt_args)
    logging.debug(cb_args)
    
    if preproc_file is not None:
        preproc = TransformList.load(preproc_file)
    else:
        preproc = None
        
    sg = G(data_path, train_list,
           shuffle_seqs=True, reset_rng=False,
           transform=preproc, **sg_args)
    max_length = sg.max_seq_length
    gen_val = None
    if val_list is not None:
        sg_val = G(data_path, val_list,
                    transform=preproc,
                    shuffle_seqs=False, reset_rng=True,
                    **sg_args)
        max_length = max(max_length, sg_val.max_seq_length)
        gen_val = data_generator(sg_val, max_length)

    gen_train = data_generator(sg, max_length)
    
    logging.info('max length: %d' % max_length)
    
    t1 = time.time()
    if freeze_prepool:
        model.freeze_prepool_net()
    if freeze_prepool_layers is not None:
        model.freeze_prepool_layers(freeze_prepool_layers)
    if freeze_postpool_layers is not None:
        model.freeze_postpool_layers(freeze_postpool_layers)
    
    model.build(max_length)
    
    cb = KCF.create_callbacks(model, output_path, **cb_args)
    opt = KOF.create_optimizer(**opt_args)
    model.compile(metrics=['accuracy'], optimizer=opt)
    
    h = model.fit_generator(gen_train, validation_data=gen_val,
                            steps_per_epoch=sg.steps_per_epoch,
                            validation_steps=sg_val.steps_per_epoch,
                            initial_epoch=sg.cur_epoch,
                            epochs=epochs, callbacks=cb, max_queue_size=10)
                          
    logging.info('Train elapsed time: %.2f' % (time.time() - t1))
    
    model.save(output_path + '/model')


    
if __name__ == "__main__":

    parser=argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        fromfile_prefix_chars='@',
        description='Train sequence embeddings')

    parser.add_argument('--data-path', dest='data_path', required=True)
    parser.add_argument('--train-list', dest='train_list', required=True)
    parser.add_argument('--val-list', dest='val_list', default=None)
    parser.add_argument('--prepool-net', dest='prepool_net_path', required=True)
    parser.add_argument('--postpool-net', dest='postpool_net_path', required=True)

    parser.add_argument('--init-path', dest='init_path', default=None)
    parser.add_argument('--preproc-file', dest='preproc_file', default=None)
    parser.add_argument('--output-path', dest='output_path', required=True)

    SeqEmbed.add_argparse_args(parser)
    G.add_argparse_args(parser)
    KOF.add_argparse_args(parser)
    KCF.add_argparse_args(parser)


    parser.add_argument('--loss', dest='loss', default='categorical_crossentropy',
                        choices=['categorical_crossentropy', 'categorical_hinge', 'categorical_mbr'])
    parser.add_argument('--freeze-prepool', dest='freeze_prepool',
                        default=False, action='store_true')
    parser.add_argument('--freeze-prepool-layers', dest='freeze_prepool_layers',
                        default=None, nargs='+')
    parser.add_argument('--freeze-postpool-layers', dest='freeze_postpool_layers',
                        default=None, nargs='+')

    parser.add_argument('--epochs', dest='epochs', default=1000, type=int)
    parser.add_argument('-v', '--verbose', dest='verbose', default=1, choices=[0, 1, 2, 3], type=int)
    
    args=parser.parse_args()
    config_logger(args.verbose)
    del args.verbose
    logging.debug(args)
        
    train_embed(**vars(args))

            
