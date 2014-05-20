#!/usr/bin/env python
# coding=utf-8
"""
This is an example experiment of how you might use sacred together with
pylstm.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment, InfoUpdater
from pylstm import *

ex = Experiment("Example1")


@ex.config
def cfg():
    dataset = ["/home/greff/Datasets/UCR.hdf5", "coffee"]

    # === Set up Network ===
    verbose = False
    hidden_units = 10

    net = build_net(InputLayer(1) >>
                    LstmLayer(hidden_units) >>
                    LstmLayer(hidden_units) >>
                    ForwardLayer(2, act_func='softmax'))

    net.initialize(Gaussian(0.2))
    net.error_func = MultiClassCrossEntropyError
    network = get_description(net)

    # === Set up Trainer ===
    tr = Trainer(SgdStep(learning_rate=0.001), verbose=verbose)
    tr.add_stopper(MaxEpochsSeen(10))
    tr.add_monitor(PrintError())
    trainer = get_description(tr)


@ex.main
def main(network, trainer, dataset, verbose):

    net = create_from_description(network)
    tr = create_from_description(trainer)
    ds = load_dataset(*dataset)

    tr.add_monitor(MonitorClassificationError(Online(*ds['test'], verbose=False)))
    tr.add_monitor(InfoUpdater(ex, tr.monitors))
    tr.train(net,
             Online(*ds['training'], verbose=verbose),
             Online(*ds['test'], verbose=verbose))

    net.forward_pass(ds['test'][0])
    return net.calculate_error(ds['test'][1])

if __name__ == '__main__':
    ex.run()