from sacred import optional as opt


def set_seed(seed):
    tf = opt.get_tensorflow()
    tf.set_random_seed(seed)
