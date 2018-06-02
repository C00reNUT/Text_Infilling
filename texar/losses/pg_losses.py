#
"""
Various loss functions for policy gradients.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

from texar.losses.losses_utils import mask_and_reduce

# pylint: disable=too-many-arguments, protected-access

__all__ = [
    "pg_loss_with_logits",
    "pg_loss_with_log_probs"
]

def pg_loss_with_logits(actions,
                        logits,
                        advantages,
                        rank=None,
                        batched=False,
                        sequence_length=None,
                        average_across_batch=True,
                        average_across_timesteps=False,
                        average_across_remaining=False,
                        sum_over_batch=False,
                        sum_over_timesteps=True,
                        sum_over_remaining=True,
                        time_major=False):
    """Policy gradient loss with logits. Used for discrete actions.

    pg_loss = mean( SG(advantages) * -log_prob( SG(actions) )  ),
    where SG(.) is stop_gradient(.)

    All arguments except :attr:`logits` and :attr:`actions` are the same as
    :func:`pg_loss_with_log_probs`.

    Args:
        actions: Tensor of shape
            `[(batch_size,) max_time, d_2, ..., d_rank]` and dtype
            `int32` or `int64`.
            The rank of the Tensor is specified with :attr:`rank`.

            The batch dimension exists only if :attr:`batched` is `True`.

            The batch and time dimensions
            are exchanged, i.e., `[max_time, batch_size, ...]` if
            :attr:`time_major` is `True`.
        logits: Unscaled log probabilities of shape
            `[(batch_size,) max_time, d_2, ..., d_{rank+1}]`
            and dtype `float32` or `float64`.
        advantages: Tensor of shape
            `[(batch_size,) max_time, d_2, ..., d_rank]` and
            dtype `float32` or `float64`.
        rank (int, optional): The rank of :attr:`actions`.
            If `None` (default), :attr:`rank`=1 if :attr:`batched` is `False`,
            and :attr:`rank`=2 if :attr:`batched` is `True`.
        batched (bool): `True` if the inputs are batched.
        sequence_length (optional): A Tensor of shape `[batch_size]`.
            Time steps beyond the respective sequence lengths will have zero
            losses. Used if :attr:`batched` is `True`.
        average_across_timesteps (bool): If set, average the loss across
            the time dimension. Must not set :attr:`average_across_timesteps`
            and :attr:`sum_over_timesteps` at the same time.
        average_across_batch (bool): If set, average the loss across the
            batch dimension. Must not set :attr:`average_across_batch`'
            and :attr:`sum_over_batch` at the same time.
            Ignored if :attr:`batched` is `False`.
        average_across_remaining (bool): If set, average the sequence across the
            remaining dimensions. Must not set :attr:`average_across_remaining`'
            and :attr:`sum_over_remaining` at the same time. Ignored if
            no more dimensions other than the batch and time dimensions.
        sum_over_timesteps (bool): If set, sum the loss across the
            time dimension. Must not set :attr:`average_across_timesteps`
            and :attr:`sum_over_timesteps` at the same time.
        sum_over_batch (bool): If set, sum the loss across the
            batch dimension. Must not set :attr:`average_across_batch`
            and :attr:`sum_over_batch` at the same time.
            Ignored if :attr:`batched` is `False`.
        sum_over_remaining (bool): If set, sum the loss across the
            remaining dimension. Must not set :attr:`average_across_remaining`
            and :attr:`sum_over_remaining` at the same time. Ignored if
            no more dimensions other than the batch and time dimensions.
        time_major (bool): The shape format of the inputs. If `True`,
            :attr:`logits`, :attr:`actions` and :attr:`advantages` must
            have shape `[max_time, batch_size, ...]`. If `False` (default),
            they must have shape `[batch_size, max_time, ...]`.
            Ignored if :attr:`batched` is `False`.

    Returns:
        A Tensor containing the loss to minimize, whose rank depends on the
        reduce arguments. For example, the batch dimension is reduced if
        either :attr:`average_across_batch` or :attr:`sum_over_batch` is
        `True`, which makes the rank of output tensor decrease by 1.
    """
    actions = tf.stop_gradient(actions)
    neg_log_probs = tf.nn.sparse_softmax_cross_entropy_with_logits(
        logits=logits, labels=actions)
    return pg_loss_with_log_probs(
        log_probs=-neg_log_probs,
        advantages=advantages,
        rank=rank,
        batched=batched,
        sequence_length=sequence_length,
        average_across_batch=average_across_batch,
        average_across_timesteps=average_across_timesteps,
        average_across_remaining=average_across_remaining,
        sum_over_batch=sum_over_batch,
        sum_over_timesteps=sum_over_timesteps,
        sum_over_remaining=sum_over_remaining,
        time_major=time_major)

def pg_loss_with_log_probs(log_probs,
                           advantages,
                           rank=None,
                           batched=False,
                           sequence_length=None,
                           average_across_batch=True,
                           average_across_timesteps=False,
                           average_across_remaining=False,
                           sum_over_batch=False,
                           sum_over_timesteps=True,
                           sum_over_remaining=True,
                           time_major=False):
    """Policy gradient loss with log probs of actions.

    pg_loss = mean( SG(advantages) * -log_probs ),
    where SG(.) is stop_gradient(.)

    All arguments except :attr:`log_probs` are the same as
    :func:`pg_loss_with_logits`.

    Args:
        log_probs: Log probabilities of shape
            `[(batch_size,) max_time, ..., d_rank]` and dtype `float32`
            or `float64`. The rank of the Tensor is specified
            with :attr:`rank`.

            The batch dimension exists only if :attr:`batched` is `True`.

            The batch and time dimensions are exchanged, i.e.,
            `[max_time, batch_size, ...]` if :attr:`time_major` is `True`.
        advantages: Tensor of shape
            `[(batch_size,) max_time, d_2, ..., d_rank]` and
            dtype `float32` or `float64`.

            The batch dimension exists only if
            :attr:`batched` is `True`.

            The batch and time dimensions
            are exchanged, i.e., `[max_time, batch_size, ...]` if
            :attr:`time_major` is `True`.
        rank (int, optional): The rank of :attr:`log_probs`.
            If `None` (default), :attr:`rank`=1 if :attr:`batched`==`False`,
            and :attr:`rank`=2 if :attr:`batched`==`True`.
        batched (bool): `True` if the inputs are batched.
        sequence_length (optional): A Tensor of shape `[batch_size]`.
            Time steps beyond the respective sequence lengths will have zero
            losses. Used if :attr:`batched` is `True`.
        average_across_timesteps (bool): If set, average the loss across
            the time dimension. Must not set :attr:`average_across_timesteps`
            and :attr:`sum_over_timesteps` at the same time.
        average_across_batch (bool): If set, average the loss across the
            batch dimension. Must not set :attr:`average_across_batch`'
            and :attr:`sum_over_batch` at the same time.
            Ignored if :attr:`batched` is `False`.
        average_across_remaining (bool): If set, average the sequence across the
            remaining dimensions. Must not set :attr:`average_across_remaining`'
            and :attr:`sum_over_remaining` at the same time. Ignored if
            no more dimensions other than the batch and time dimensions.
        sum_over_timesteps (bool): If set, sum the loss across the
            time dimension. Must not set :attr:`average_across_timesteps`
            and :attr:`sum_over_timesteps` at the same time.
        sum_over_batch (bool): If set, sum the loss across the
            batch dimension. Must not set :attr:`average_across_batch`
            and :attr:`sum_over_batch` at the same time.
            Ignored if :attr:`batched` is `False`.
        sum_over_remaining (bool): If set, sum the loss across the
            remaining dimension. Must not set :attr:`average_across_remaining`
            and :attr:`sum_over_remaining` at the same time. Ignored if
            no more dimensions other than the batch and time dimensions.
        time_major (bool): The shape format of the inputs. If `True`,
            :attr:`log_probs` and :attr:`advantages` must have shape
            `[max_time, batch_size, ...]`. If `False` (default),
            they must have shape `[batch_size, max_time, ...]`.
            Ignored if :attr:`batched` is `False`.

    Returns:
        A Tensor containing the loss to minimize, whose rank depends on the
        reduce arguments. For example, the batch dimension is reduced if
        either :attr:`average_across_batch` or :attr:`sum_over_batch` is
        `True`, which makes the rank of output tensor decrease by 1.
    """
    advantages = tf.stop_gradient(advantages)

    losses = -log_probs * advantages

    if rank is None:
        rank = 2 if batched else 1
    if batched:
        losses = mask_and_reduce(
            losses,
            sequence_length,
            rank=rank,
            average_across_batch=average_across_batch,
            average_across_timesteps=average_across_timesteps,
            average_across_remaining=average_across_remaining,
            sum_over_batch=sum_over_batch,
            sum_over_timesteps=sum_over_timesteps,
            sum_over_remaining=sum_over_remaining,
            time_major=time_major)
    elif rank > 1:
        if average_across_remaining and sum_over_remaining:
            raise ValueError("Only one of `average_across_remaining` and "
                             "`sum_over_remaining` can be set.")
        if average_across_remaining:
            losses = tf.reduce_mean(losses, axis=range(1, rank))
        elif sum_over_remaining:
            losses = tf.reduce_sum(losses, axis=range(1, rank))

    if average_across_timesteps and sum_over_timesteps:
        raise ValueError("Only one of `average_across_timesteps` and "
                         "`sum_over_timesteps` can be set.")
    if average_across_timesteps:
        losses = tf.reduce_mean(losses)
    elif sum_over_timesteps:
        losses = tf.reduce_mean(losses)

    return losses
