#
"""
Unit tests for RNN encoders.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import tensorflow as tf

from texar.modules.encoders.hierarchical_encoders import HierarchicalRNNEncoder

# pylint: disable=too-many-locals

class HierarchicalRNNEncoderTest(tf.test.TestCase):
    def test_trainable_variables(self):
        encoder = HierarchicalRNNEncoder()

        inputs = tf.random_uniform(
            [3, 2, 3, 4],
            maxval=1,
            minval=-1,
            dtype=tf.float32)
        _, _ = encoder(inputs)

        self.assertEqual(
            len(encoder.trainable_variables), 
            len(encoder.encoder_major.trainable_variables) + \
            len(encoder.encoder_minor.trainable_variables))

    def test_encode(self):
        encoder = HierarchicalRNNEncoder()

        batch_size = 16
        max_major_time = 8
        max_minor_time = 6
        dim = 10
        inputs = tf.random_uniform(
            [batch_size, max_major_time, max_minor_time, dim],
            maxval=1,
            minval=-1,
            dtype=tf.float32)
        outputs, state = encoder(inputs) 

        cell_dim = encoder.encoder_major.hparams.rnn_cell.kwargs.num_units

        with self.test_session() as sess:
            sess.run(tf.global_variables_initializer())
            outputs_, state_ = sess.run([outputs, state])
            self.assertEqual(state_[0].shape, (batch_size, cell_dim))

    def test_order(self):
        encoder = HierarchicalRNNEncoder()

        batch_size = 16
        max_major_time = 8
        max_minor_time = 6
        dim = 10
        inputs = tf.random_uniform(
            [batch_size, max_major_time, max_minor_time, dim],
            maxval=1,
            minval=-1,
            dtype=tf.float32)

        outputs, state = encoder(inputs, order='btu', time_major=False)
        outputs, state = encoder(inputs, order='utb', time_major=True)
        outputs, state = encoder(inputs, order='tbu', time_major_major=True)
        outputs, state = encoder(inputs, order='ubt', time_major_minor=True)

    def test_depack(self):
        hparams = {
            "encoder_major_type": "BidirectionalRNNEncoder",
            "encoder_major_hparams": {
                "rnn_cell_fw": {
                    "type": "LSTMCell",
                    "kwargs": {
                        "num_units": 100
                    }
                }
            }
        }
        encoder = HierarchicalRNNEncoder(hparams=hparams)

        batch_size = 16
        max_major_time = 8
        max_minor_time = 6
        dim = 10
        inputs = tf.random_uniform(
            [batch_size, max_major_time, max_minor_time, dim],
            maxval=1,
            minval=-1,
            dtype=tf.float32)

        outputs, state = encoder(inputs)

        self.assertEqual(
            encoder.states_minor_before_medium.h.shape[1], 
            encoder.states_minor_after_medium.shape[1])

if __name__ == "__main__":
    tf.test.main()
