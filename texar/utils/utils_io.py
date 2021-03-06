# -*- coding: utf-8 -*-
#
"""
Utility functions related to input/output.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from io import open # pylint: disable=redefined-builtin
import os
#import logging
import importlib
import yaml

import tensorflow as tf
from tensorflow import gfile

as_text = tf.compat.as_text

__all__ = [
    "write_paired_text",
    "load_config_single",
    "load_config"
]

#def get_tf_logger(fname,
#                  verbosity=tf.logging.INFO,
#                  to_stdio=False,
#                  stdio_verbosity=None):
#    """Creates TF logger that allows to specify log filename and whether to
#    print to stdio at the same time.
#
#    Args:
#        fname (str): The log filename.
#        verbosity: The threshold for what messages will be logged. Default is
#            `INFO`. Other options include `DEBUG`, `ERROR`, `FATAL`, and `WARN`.
#            See :tf_main:`tf.logging <logging>`.
#        to_stdio (bool): Whether to print messages to stdio at the same time.
#        stido_verbosity (optional): The verbosity level when printing to stdio.
#            If `None` (default), the level is set to be the same as
#            :attr:`verbosity`. Ignored if :attr:`to_stdio` is False.
#
#    Returns:
#        The TF logger.
#    """

def _load_config_python(fname):
    config = {}

    config_module = importlib.import_module(fname.rstrip('.py'))
    for key in dir(config_module):
        if not (key.startswith('__') and key.endswith('__')):
            config[key] = getattr(config_module, key)

    return config

def _load_config_yaml(fname):
    with gfile.GFile(fname) as config_file:
        config = yaml.load(config_file)
    return config

def load_config_single(fname, config=None):
    """Loads config from a single file.

    The config file can be either a Python file (with suffix '.py')
    or a YAML file. If the filename is not suffixed with '.py', the file is
    parsed as YAML.

    Args:
        fname (str): The config file name.
        config (dict, optional): A config dict to which new configurations are
            added. If `None`, a new config dict is created.

    Returns:
        A `dict` of configurations.
    """
    if fname.endswith('.py'):
        new_config = _load_config_python(fname)
    else:
        new_config = _load_config_yaml(fname)

    if config is None:
        config = new_config
    else:
        for key, value in new_config.items():
            if key in config:
                if isinstance(config[key], dict):
                    config[key].update(value)
                else:
                    config[key] = value
            else:
                config[key] = value

    return config

def load_config(config_path, config=None):
    """Loads configs from (possibly multiple) file(s).

    Args:
        config_path: Paths to configuration files. This can be a `list` of
            config file names, or a path to a directory in which all files
            are loaded, or a string of multiple file names separated by commas.
        config (dict, optional): A config dict to which new configurations are
            added. If `None`, a new config dict is created.

    Returns:
        A `dict` of configurations.
    """
    fnames = []
    if isinstance(config_path, (list, tuple)):
        fnames = list(config_path)
    elif gfile.IsDirectory(config_path):
        for fname in gfile.ListDirectory(config_path):
            fname = os.path.join(config_path, fname)
            if not gfile.IsDirectory(fname):
                fnames.append(fname)
    else:
        for fname in config_path.split(","):
            fname = fname.strip()
            if not fname:
                continue
            fnames.append(fname)

    if config is None:
        config = {}

    for fname in fnames:
        config = load_config_single(fname, config)

    return config

def write_paired_text(src, tgt, fname, append=False, mode='h', sep='\t'):
    """Writes paired text to a file.

    Args:
        src: A list (or array) of `str` source text.
        ttg: A list (or array) of `str` target text.
        fname (str): The output filename.
        append (bool): Whether appending to the end of the file if exists.
        mode (str): The mode of writing, with the following options:

            - :attr:`'h'`: The "horizontal" mode. Each source target pair is \
                written in one line, intervened with :attr:`sep`, e.g.,

                    source_1 target_1
                    source_2 target_2

            - :attr:`'v'`: The "vertical" mode. Each source target pair is \
                written in two consecutive lines, e.g,

                    source_1
                    target_1
                    source_2
                    target_2

            - :attr:`'s'`: The "separate" mode. Each source target pair is \
                    written in corresponding lines of two files named \
                    as :attr:`fname`.src and :attr:`fname`.tgt, respectively.
        sep (str): The string intervening between source and target. Used
            when :attr:`mode`='h'.

    Returns:
        The fileanme(s). If :attr:`mode`=='h' or :attr:`mode`=='v', returns
        :attr:`fname`. If :attr:`mode`=='s', returns a list of filenames
        `[':attr:`fname`.src', ':attr:`fname`.tgt']`.
    """
    fmode = 'a' if append else 'w'
    if mode == 's':
        fn_src = '{}.src'.format(fname)
        fn_tgt = '{}.tgt'.format(fname)
        with open(fn_src, fmode, encoding='utf-8') as fs:
            fs.write(as_text('\n'.join(src)))
            fs.write('\n')
        with open(fn_tgt, fmode, encoding='utf-8') as ft:
            ft.write(as_text('\n'.join(tgt)))
            ft.write('\n')
        return fn_src, fn_tgt
    else:
        with open(fname, fmode, encoding='utf-8') as f:
            for s, t in zip(src, tgt):
                if mode == 'h':
                    text = '{}{}{}\n'.format(as_text(s), sep, as_text(t))
                    f.write(as_text(text))
                elif mode == 'v':
                    text = '{}\n{}\n'.format(as_text(s), as_text(t))
                    f.write(as_text(text))
                else:
                    raise ValueError('Unknown mode: {}'.format(mode))
        return fname
