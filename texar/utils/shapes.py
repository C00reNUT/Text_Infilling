#
"""
Utility functions related to tensor shapes.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

# pylint: disable=no-name-in-module, protected-access, no-member, invalid-name

import numpy as np

import tensorflow as tf
from tensorflow.python.util import nest
from tensorflow.python.ops import rnn
from tensorflow.python.framework import ops

__all__ = [
    "transpose_batch_time",
    "get_batch_size",
    "get_rank",
    "mask_sequences",
    "_mask_sequences_tensor",
    "_mask_sequences_py",
    "flatten"
]


def transpose_batch_time(inputs):
    """Transposes inputs between time-major and batch-major.

    Args:
        inputs: A Tensor of shape `[batch_size, max_time, ...]` (batch-major)
            or `[max_time, batch_size, ...]` (time-major), or a (possibly
            nested) tuple of such elements.

    Returns:
        A Tensor with transposed batch and time dimensions of inputs.
    """
    flat_input = nest.flatten(inputs)
    flat_input = [ops.convert_to_tensor(input_) for input_ in flat_input]
    # pylint: disable=protected-access
    flat_input = [rnn._transpose_batch_time(input_) for input_ in flat_input]
    return nest.pack_sequence_as(structure=inputs, flat_sequence=flat_input)

def get_batch_size(tensor):
    """Returns a unit `Tensor` representing the batch size, i.e.,
    the size of the 1st dimension of :attr:`tensor`.
    """
    return tf.shape(tensor)[0]


def get_rank(tensor):
    """Returns the tensor rank as a python `int`. The input tensor can also be
    a python array.

    Args:
        tensor: A Tensor or python array.

    Returns:
        A python `int` representing the rank of :attr:`tensor`. Returns
        `None` if the rank cannot be determined.
    """
    if tf.contrib.framework.is_tensor(tensor):
        shape = tensor.shape
        try:
            rank = len(shape.as_list())
        except ValueError: # when `shape==TensorShape(None)`
            rank = None
    else:
        array = np.asarray(tensor)
        rank = array.ndim
    return rank

def mask_sequences(sequence,
                   sequence_length,
                   dtype=None,
                   time_major=False,
                   tensor_rank=2):
    """Masks out sequence entries that are beyond the respective sequence
    lengths. Masks along the time dimension.

    :attr:`sequence` and :attr:`sequence_length` can either be python
    arrays or Tensors, respectively. If both are python arrays (or None), the
    return will be a python array as well.

    :attr:`tensor_rank` is ignored when :attr:`sequence` and
    :attr:`sequence_length` are both python arrays (rather than Tensors).

    Args:
        sequence: A Tensor or python array of sequence values.

            If `time_major=False` (default), this must be a Tensor of shape:
                `[batch_size, max_time, ...]`.

            If `time_major=True`, this must be a Tensor of shape:
                `[max_time, batch_size, ...].`
        sequence_length: A Tensor or python array of shape `[batch_size]`.
            Time steps beyond the respective sequence lengths will be
            made zero.
        dtype (dtype): Type of :attr:`sequence`. If `None`, infer from
            :attr:`sequence` automatically.
        time_major (bool): The shape format of the inputs. If `True`,
            :attr:`sequence` must have shape
            `[max_time, batch_size, ...]`.
            If `False` (default), :attr:`sequence` must have
            shape `[batch_size, max_time, ...]`.
        tensor_rank (int): The number of dimensions of :attr:`sequence`.
            Default is 2, i.e., :attr:`sequence` is a 2D Tensor consisting
            of batch and time dimensions. Ignored if both :attr:`sequence`
            and :attr:`sequence_length` are python arrays.

    Returns:
        The masked sequence, i.e., a Tensor or python array of the same shape
        as :attr:`sequence` but with masked-out entries (set to zero).

        If both :attr:`sequence` and :attr:`sequence_length` are python
        arrays, the returned value is a python array as well.
    """
    is_tensor = tf.contrib.framework.is_tensor
    if is_tensor(sequence) or is_tensor(sequence_length):
        return _mask_sequences_tensor(
            sequence, sequence_length, dtype, time_major, tensor_rank)
    else:
        return _mask_sequences_py(
            sequence, sequence_length, dtype, time_major)

def _mask_sequences_tensor(sequence,
                           sequence_length,
                           dtype=None,
                           time_major=False,
                           tensor_rank=2):
    """Masks out sequence entries that are beyond the respective sequence
    lengths. Masks along the time dimension.

    Args:
        sequence: A Tensor of sequence values.

            If `time_major=False` (default), this must be a Tensor of shape:
                `[batch_size, max_time, d_2, ..., d_rank]`, where the rank of
                the Tensor is specified with :attr:`tensor_rank`.

            If `time_major=True`, this must be a Tensor of shape:
                `[max_time, batch_size, d_2, ..., d_rank].`
        sequence_length: A Tensor of shape `[batch_size]`. Time steps beyond
            the respective sequence lengths will be made zero.
        dtype (dtype): Type of :attr:`sequence`. If `None`, infer from
            :attr:`sequence` automatically.
        time_major (bool): The shape format of the inputs. If `True`,
            :attr:`sequence` must have shape
            `[max_time, batch_size, d_2, ..., d_rank]`.
            If `False` (default), :attr:`sequence` must have
            shape `[batch_size, max_time, d_2, ..., d_rank]`.
        tensor_rank (int): The number of dimensions of :attr:`sequence`.
            Default is 2, i.e., :attr:`sequence` is a 2D Tensor consisting
            of batch and time dimensions.

    Returns:
        The masked sequence, i.e., a Tensor of the same shape as
        :attr:`sequence` but with masked-out entries (set to zero).
    """
    if tensor_rank is None:
        tensor_rank = 2
    if tensor_rank < 2:
        raise ValueError(
            "tensor_rank must be > 2. Got tensor_rank = {}".format(tensor_rank))
    if time_major:
        sequence = rnn._transpose_batch_time(sequence)
    max_time = tf.to_int32(tf.shape(sequence)[1])
    if dtype is None:
        dtype = sequence.dtype
    mask = tf.sequence_mask(
        tf.to_int32(sequence_length), max_time, dtype=dtype)
    for _ in range(2, tensor_rank):
        mask = tf.expand_dims(mask, axis=-1)
    sequence = sequence * mask
    if time_major:
        sequence = rnn._transpose_batch_time(sequence)
    return sequence

def _mask_sequences_py(sequence,
                       sequence_length,
                       dtype=None,
                       time_major=False):
    """Masks out sequence entries that are beyond the respective sequence
    lengths. Masks along the time dimension.

    This is the numpy version of :func:`texar.utils.mask_sequences`.

    Args:
        sequence: An python array of sequence values.

            If `time_major=False` (default), this must be an array of shape:
                `[batch_size, max_time, ...]`

            If `time_major=True`, this must be a Tensor of shape:
                `[max_time, batch_size, ...].`
        sequence_length: An array of shape `[batch_size]`. Time steps beyond
            the respective sequence lengths will be made zero.
        dtype (dtype): Type of :attr:`sequence`. If `None`, infer from
            :attr:`sequence` automatically.
        time_major (bool): The shape format of the inputs. If `True`,
            :attr:`sequence` must have shape
            `[max_time, batch_size, ...]`.
            If `False` (default), :attr:`sequence` must have
            shape `[batch_size, max_time, ...]`.

    Returns:
        The masked sequence, i.e., an array of the same shape as
        :attr:`sequence` but with masked-out entries (set to zero).
    """
    sequence = np.array(sequence)
    sequence_length = np.array(sequence_length)

    rank = sequence.ndim
    if rank < 2:
        raise ValueError("`sequence` must be 2D or higher order.")
    batch_size = sequence.shape[0]
    max_time = sequence.shape[1]
    dtype = dtype or sequence.dtype

    if time_major:
        sequence = np.transpose(sequence, axes=[1, 0, 2])

    steps = np.tile(np.arange(max_time), [batch_size, 1])
    mask = np.asarray(steps < sequence_length[:, None], dtype=dtype)
    for _ in range(2, rank):
        mask = np.expand_dims(mask, -1)

    sequence = sequence * mask

    if time_major:
        sequence = np.transpose(sequence, axes=[1, 0, 2])

    return sequence


def flatten(tensor, preserve_dims, flattened_dim=None):
    """Flattens a tensor whiling keeping several leading dimensions.

    :attr:`preserve_dims` must < tensor's rank

    Args:
        tensor: A Tensor to flatten.
        preserve_dims (int): The number of leading dimensions to preserve.
        flatterned_dim (int, optional): The size of the resulting flattened
            dimension. If not given, infer automatically, which can cause
            a statically unknown dimension size.

    Returns:
        A Tensor with rank :attr:`perserve_dims`+1.

    Example:
        .. code-block:: python

            x = tf.ones(shape=[d_1, d_2, d_3, d_4])
            y = flatten(x, 2) # y.shape == [d_1, d_2, d_3 * d_4]
    """
    if flattened_dim is None:
        flattened_dim = -1
    shape = tf.concat([tf.shape(tensor)[:preserve_dims], [flattened_dim]],
                      axis=0)
    tensor_ = tf.reshape(tensor, shape)
    return tensor_

def shape_list(x):
    """Returns the tensor shape.

    Returns static shape when possible.

    Returns:

        - If the rank of :attr:`x` is unknown, returns the dynamic shape: \
        `tf.shape(x)`
        - Otherwise, returns a list of dims, each of which is either an `int` \
        whenever it can be statically determined, or a scalar Tensor.
    """
    x = tf.convert_to_tensor(x)
    # If unknown rank, return dynamic shape
    if x.get_shape().dims is None:
        return tf.shape(x)
    static = x.get_shape().as_list()
    shape = tf.shape(x)
    ret = []
    for i, dim in enumerate(static):
        if dim is None:
            dim = shape[i]
        ret.append(dim)
    return ret
