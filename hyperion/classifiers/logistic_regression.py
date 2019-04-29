"""
 Copyright 2018 Johns Hopkins University  (Author: Jesus Villalba)
 Apache 2.0  (http://www.apache.org/licenses/LICENSE-2.0)
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from six.moves import xrange

import logging
import numpy as np

from  sklearn.linear_model import LogisticRegression as LR

from ..hyp_defs import float_cpu
from ..hyp_model import HypModel
from ..utils.math import softmax


class LogisticRegression(HypModel):

    def __init__(self, A=None, b=None, penalty='l2', lambda_reg=1e-5,
                 use_bias=True, bias_scaling=1,
                 priors=None, random_state=None, solver='lbfgs', max_iter=100,
                 dual=False, tol=0.0001, multi_class='multinomial', verbose=0, warm_start=True, num_jobs=1,
                 lr_seed=1024, **kwargs):
        
        """ Wrapper for sktlearn logistic regression. 
         penalty : str, ‘l1’ or ‘l2’, default: ‘l2’ ,
                  Used to specify the norm used in the penalization. The ‘newton-cg’, ‘sag’ and ‘lbfgs’ solvers support only l2 penalties.
                   New in version 0.19: l1 penalty with SAGA solver (allowing ‘multinomial’ + L1)
         dual : bool, default: False
                Dual or primal formulation. Dual formulation is only implemented for l2 penalty with liblinear solver. Prefer dual=False when n_samples > n_features.
         tol : float, default: 1e-4
               Tolerance for stopping criteria.
         lambda_reg : float, default: 1e-5
                      Regularization strength; must be a positive float. 
         use_bias : bool, default: True
                    Specifies if a constant (a.k.a. bias or intercept) should be added to the decision function.
         bias_scaling : float, default 1.
                        Useful only when the solver ‘liblinear’ is used and use_bias is set to True. 
                        In this case, x becomes [x, bias_scaling], i.e. a “synthetic” feature with constant value equal to intercept_scaling is appended to the instance vector. The intercept becomes intercept_scaling * synthetic_feature_weight.
                        Note! the synthetic feature weight is subject to l1/l2 regularization as all other features. To lessen the effect of regularization on synthetic feature weight (and therefore on the intercept) bias_scaling has to be increased.
         priors : dict or ‘balanced' default: None
                 Weights associated with classes in the form {class_label: weight}. If not given, all classes are supposed to have weight one.
                 The “balanced” mode uses the values of y to automatically adjust weights inversely proportional to class frequencies in the input data as n_samples / (n_classes * np.bincount(y)).
                 Note that these weights will be multiplied with sample_weight (passed through the fit method) if sample_weight is specified.
         random_state : int, RandomState instance or None, optional, default: None
                        The seed of the pseudo random number generator to use when shuffling the data. If int, random_state is the seed used by the random number generator; If RandomState instance, random_state is the random number generator; . Used when solver == ‘sag’ or ‘liblinear’.
         solver : {‘newton-cg’, ‘lbfgs’, ‘liblinear’, ‘sag’, ‘saga’},
                  default: ‘liblinear’ Algorithm to use in the optimization problem.
                  For small datasets, ‘liblinear’ is a good choice, whereas ‘sag’ and
                  ‘saga’ are faster for large ones.
                  For multiclass problems, only ‘newton-cg’, ‘sag’, ‘saga’ and ‘lbfgs’
                  handle multinomial loss; ‘liblinear’ is limited to one-versus-rest schemes.
                  ‘newton-cg’, ‘lbfgs’ and ‘sag’ only handle L2 penalty, whereas
                  ‘liblinear’ and ‘saga’ handle L1 penalty.
                  Note that ‘sag’ and ‘saga’ fast convergence is only guaranteed on features with approximately the same scale.
                  New in version 0.17: Stochastic Average Gradient descent solver.
                  New in version 0.19: SAGA solver.
         max_iter : int, default: 100
                    Useful only for the newton-cg, sag and lbfgs solvers. Maximum number of iterations taken for the solvers to converge.
         multi_class : str, {‘ovr’, ‘multinomial’}, default: ‘ovr’
                      Multiclass option can be either ‘ovr’ or ‘multinomial’. If the option chosen is ‘ovr’, then a binary problem is fit for each label. Else the loss minimised is the multinomial loss fit across the entire probability distribution. Does not work for liblinear solver.
                      New in version 0.18: Stochastic Average Gradient descent solver for ‘multinomial’ case.
         verbose : int, default: 0
                   For the liblinear and lbfgs solvers set verbose to any positive number for verbosity.
         warm_start : bool, default: False
                      When set to True, reuse the solution of the previous call to fit as initialization, otherwise, just erase the previous solution. Useless for liblinear solver.
                      New in version 0.17: warm_start to support lbfgs, newton-cg, sag, saga solvers.
         n_jobs : int, default: 1
                  Number of CPU cores used when parallelizing over classes if multi_class=’ovr’”. This parameter is ignored when the ``solver``is set to ‘liblinear’ regardless of whether ‘multi_class’ is specified or not. If given a value of -1, all cores are used.
        """
        super(LogisticRegression, self).__init__(**kwargs)

        if random_state is None:
            random_state = np.random.RandomState(seed=lr_seed)

        if bias_scaling is None:
            if use_bias and solver == 'liblinear':
                bias_scaling = 100
            else:
                bias_scaling = 1

        self.use_bias = use_bias
        self.bias_scaling = bias_scaling
        self.priors = priors
        self.lambda_reg = lambda_reg
        self.multi_class = multi_class
        self.lr = LR(penalty=penalty, C=1/lambda_reg,
                     dual=dual, tol=tol,
                     fit_intercept=use_bias, intercept_scaling=bias_scaling,
                     random_state=random_state,
                     solver=solver, max_iter=max_iter,
                     multi_class=multi_class,
                     verbose=verbose, warm_start=warm_start, n_jobs=num_jobs)

        if A is not None:
            self.lr.coef_ = A.T

        if b is not None:
            self.lr.intercept_ = b/self.bias_scaling


    @property
    def A(self):
        return self.lr.coef_.T

    @property
    def b(self):
        return self.lr.intercept_*self.bias_scaling


    def get_config(self):
        config = { 'use_bias': self.use_bias,
                   'bias_scaling': self.bias_scaling,
                   'priors': self.priors }
        base_config = super(LogisticRegression, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


    
    def predict(self, x, eval_type='logit'):
        if x.ndim == 1:
            x = x[:, None]
        
        y = np.dot(x, self.A) + self.b

        if eval_type == 'log-post':
            y = np.log(softmax(y + np.log(self.priors), axis=1)+1e-10)
        if eval_type == 'post':
            y = softmax(y + np.log(self.priors))
        
        return y
        

    
    def fit(self, x, class_ids, sample_weight=None):
        if x.ndim == 1:
            x = x[:, None]
        num_classes = np.max(class_ids)+1
        counts = np.bincount(class_ids)
        assert num_classes == len(counts)
        
        if self.priors is None:
            priors = 1/num_classes * np.ones((num_classes,), dtype=float_cpu())
        else:
            priors = [self.priors[i] for i in xrange(num_classes)]
        class_weights = priors/counts
        
        if sample_weight is None:
            sample_weight = class_weights[class_ids]
        else:
            sample_weight *= class_weights[class_ids]
            
        self.lr.fit(x, class_ids, sample_weight=sample_weight)

        if self.multi_class == 'ovr':
            #adjust bias to produce log-llk ratios
            if len(self.lr.intercept_) == 1:
                priors = self.priors[1]
            self.lr.intercept_ -= np.log(priors/(1-priors))/self.bias_scaling
        else:
            #adjust bias to produce log-llk
            self.lr.intercept_ -= np.log(self.priors)/self.bias_scaling


            
    def save_params(self, f):
        params = { 'A': self.A,
                   'b': self.b}
        self._save_params_from_dict(f, params)
        

    @classmethod
    def load_params(cls, f, config):
        param_list = ['A', 'b']
        params = cls._load_params_to_dict(f, config['name'], param_list)
        kwargs = dict(list(config.items()) + list(params.items()))
        return cls(**kwargs)


    
    @staticmethod
    def filter_train_args(prefix=None, **kwargs):
        if prefix is None:
            p = ''
        else:
            p = prefix + '_'
            
        valid_args = ('penalty', 'lambda_reg',
                      'use_bias', 'bias_scaling', 'no_use_bias',
                      'priors', 'lr_seed',
                      'solver', 'max_iter',
                      'dual', 'tol', 'multi_class', 'verbose',
                      'warm_start', 'no_warm_start', 'num_jobs', 'name')
        d = dict((k, kwargs[p+k])
               for k in valid_args if p+k in kwargs)
        if 'no_use_bias' in d:
            d['use_bias'] = not d['no_use_bias']
        if 'no_warm_start' in d:
            d['warm_start'] = not d['no_warm_start']
        
        return d


    
    @staticmethod
    def add_argparse_train_args(parser, prefix=None):
        if prefix is None:
            p1 = '--'
            p2 = ''
        else:
            p1 = '--' + prefix + '-'
            p2 = prefix + '_'

        parser.add_argument(p1+'penalty', dest=(p2+'penalty'), 
                            default='l2', choices=['l2', 'l1'],
                            help='used to specify the norm used in the penalization')
        parser.add_argument(p1+'lambda-reg', dest=(p2+'lambda_reg'), 
                            default=1e-5, type=float,
                            help='regularization strength')
        parser.add_argument(p1+'no-use-bias', dest=(p2+'no_use_bias'),
                            default=False, action='store_true',
                            help='Not use bias')
        parser.add_argument(p1+'bias-scaling', dest=(p2+'bias_scaling'),
                            default=1.0, type=float,
                            help='useful only when the solver liblinear is used and use_bias is set to True')
        parser.add_argument(p1+'lr-seed', dest=(p2+'lr_seed'), 
                            default=1024, type=int,
                            help='random number generator seed')
        parser.add_argument(p1+'solver', dest=(p2+'solver'), 
                            default='lbfgs', choices=['newton-cg', 'lbfgs', 'liblinear', 'sag', 'saga'],
                            help='type of solver')
        parser.add_argument(p1+'max-iter', dest=(p2+'max_iter'), 
                            default=100, type=int,
                            help='only for the newton-cg, sag and lbfgs solvers')
        parser.add_argument(p1+'dual', dest=(p2+'dual'),
                            default=False, action='store_true',
                            help=('dual or primal formulation. '
                                  'Dual formulation is only implemented for l2 penalty with liblinear solver'))
        parser.add_argument(p1+'tol', dest=(p2+'tol'), default=1e-4, type=float,
                            help='tolerance for stopping criteria')
        parser.add_argument(p1+'multi-class', dest=(p2+'multi_class'), 
                            default='ovr', choices=['ovr', 'multinomial'],
                            help=('ovr fits a binary problem for each class else it minimizes the multinomial loss.'
                                  'Does not work for liblinear solver'))
        parser.add_argument(p1+'verbose', dest=(p2+'verbose'), 
                            default=0, type=int,
                            help='For the liblinear and lbfgs solvers')
        parser.add_argument(p1+'num-jobs', dest=(p2+'num_jobs'), 
                            default=1, type=int,
                            help='number of cores for ovr')
        parser.add_argument(p1+'no-warm-start', dest=(p2+'no_warm_start'),
                            default=False, action='store_true',
                            help='don\'t use previous model to start')


        parser.add_argument(p1+'name', dest=(p2+'name'), 
                            default='lr',
                            help='model name')

        

    @staticmethod
    def filter_eval_args(prefix, **kwargs):
        if prefix is None:
            p = ''
        else:
            p = prefix + '_'
        valid_args = ('model_file', 'eval_type')
        return dict((k, kwargs[p+k])
                    for k in valid_args if p+k in kwargs)


    
    @staticmethod
    def add_argparse_eval_args(parser, prefix=None):
        if prefix is None:
            p1 = '--'
            p2 = ''
        else:
            p1 = '--' + prefix + '-'
            p2 = prefix + '_'

        parser.add_argument(p1+'model-file', dest=(p2+'model_file'), required=True,
                            help=('model file'))
        parser.add_argument(p1+'eval-type', dest=(p2+'eval_type'), default='logit',
                            choices=['logit','log-post','post'],
                            help=('type of evaluation'))
                            
        

        
