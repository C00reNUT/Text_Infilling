generator_pretrain_epoch = 20
discriminator_pretrain_epoch = 15
adversial_epoch = 20

hidden_size = 200
batch_size = 64
max_num_steps = 20

enc_keep_prob_in = 1.0
dec_keep_prob_out = 1.0

log_dir = './ptb_log/'
log_file = log_dir + 'log.txt'
bleu_file = log_dir + 'bleu.txt'
ckpt = './checkpoint/ckpt'

dec_cell_hparams = {
    "type": "LSTMBlockCell",
    "kwargs": {
        "num_units": hidden_size,
        "forget_bias": 0.
    },
    "dropout": {"output_keep_prob": dec_keep_prob_out},
    "num_layers": 1
}

emb_hparams = {
    'name': 'lookup_table',
    "dim": hidden_size,
    'initializer': {
        'type': 'random_normal_initializer',
        'kwargs': {
            'mean': 0.0,
            'stddev': hidden_size**-0.5,
        },
    }
}

train_data_hparams = {
    "num_epochs": 1,
    "batch_size": batch_size,
    "seed": 123,
    "dataset": {
        "files": 'ptb_data/ptb.train.txt',
        "vocab_file": 'ptb_data/vocab.txt'
    }
}

val_data_hparams = {
    "num_epochs": 1,
    "batch_size": batch_size,
    "seed": 123,
    "dataset": {
        "files": 'ptb_data/ptb.valid.txt',
        "vocab_file": 'ptb_data/vocab.txt'
    }
}

test_data_hparams = {
    "num_epochs": 1,
    "batch_size": batch_size,
    "dataset": {
        "files": 'ptb_data/ptb.test.txt',
        "vocab_file": 'ptb_data/vocab.txt'
    }
}

g_opt_hparams = {
    "optimizer": {
        "type": "AdamOptimizer",
        "kwargs": {
            "learning_rate": 0.01
        }
    },
    "gradient_clip": {
        "type": "clip_by_global_norm",
        "kwargs": {"clip_norm": 5.}
    },
    "learning_rate_decay": {
        "type": "exponential_decay",
        "kwargs": {
            "decay_steps": 1,
            "decay_rate": 0.5,
            "staircase": True
        },
        "start_decay_step": 3
    }
}

d_opt_hparams = {
    "optimizer": {
        "type": "AdamOptimizer",
        "kwargs": {
            "learning_rate": 0.0001
        }
    }
}

update_opt_hparams = {
    "optimizer": {
        "type": "AdamOptimizer",
        "kwargs": {
            "learning_rate": 0.0004
        }
    }
}