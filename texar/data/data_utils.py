#
"""
Various utilities specific to data processing.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import tarfile
import zipfile
import logging
import collections
import numpy as np
from six.moves import urllib

import tensorflow as tf

# pylint: disable=invalid-name

__all__ = [
    "create_dir_if_needed",
    "maybe_download",
    "get_files",
    "read_words",
    "make_vocab",
    "count_file_lines"
]

Py3 = sys.version_info[0] == 3

def create_dir_if_needed(dirname):
    """Creates directory if doesn't exist
    """
    if not tf.gfile.IsDirectory(dirname):
        tf.gfile.MakeDirs(dirname)
        return True
    return False

def maybe_download(urls, path, extract=False):
    """Downloads a set of files.

    Args:
        urls: A (list of) urls to download files.
        path (str): The destination path to save the files.
        extract (bool): Whether to extract compressed files.

    Returns:
        A list of paths to the downloaded files.
    """
    create_dir_if_needed(path)

    if not isinstance(urls, (list, tuple)):
        urls = [urls]
    result = []
    for url in urls:
        filename = url.split('/')[-1]
        # If downloading from GitHub, remove suffix ?raw=True
        # from local filename
        if filename.endswith("?raw=true"):
            filename = filename[:-9]

        filepath = os.path.join(path, filename)
        result.append(filepath)

        if not tf.gfile.Exists(filepath):
            def _progress(count, block_size, total_size):
                percent = float(count * block_size) / float(total_size) * 100.
                # pylint: disable=cell-var-from-loop
                sys.stdout.write('\r>> Downloading %s %.1f%%' %
                                 (filename, percent))
                sys.stdout.flush()
            filepath, _ = urllib.request.urlretrieve(url, filepath, _progress)
            print()
            statinfo = os.stat(filepath)
            print('Successfully downloaded {} {} bytes.'.format(
                filename, statinfo.st_size))

            if extract:
                logging.info('Extract %s', filepath)
                if tarfile.is_tarfile(filepath):
                    tarfile.open(filepath, 'r').extractall(path)
                elif zipfile.is_zipfile(filepath):
                    with zipfile.ZipFile(filepath) as zfile:
                        zfile.extractall(path)
                else:
                    logging.info("Unknown compression type. Only .tar.gz, "
                                 ".tar.bz2, .tar, and .zip are supported")

    return result

def get_files(file_paths):
    """Gets a list of file paths given possibly a pattern :attr:`file_paths`.

    Adapted from `tf.contrib.slim.data.parallel_reader.get_data_files`.

    Args:
        file_paths: A (list of) path to the files. The path can be a pattern,
            e.g., /path/to/train*, /path/to/train[12]

    Returns:
        A list of file paths.

    Raises:
        ValueError: If no files are not found
    """
    if isinstance(file_paths, (list, tuple)):
        files = []
        for f in file_paths:
            files += get_files(f)
    else:
        if '*' in file_paths or '?' in file_paths or '[' in file_paths:
            files = tf.gfile.Glob(file_paths)
        else:
            files = [file_paths]
    if not files:
        raise ValueError('No data files found in %s' % (file_paths,))
    return files

def read_words(filename, newline_token=None):
    """Reads word from a file.

    Args:
        filename (str): Path to the file.
        newline_token (str): The token to replace the original newline
            token `\n`. For example, `newline_token=tx.data.SpecialTokens.EOS`.
            If `None`, no replacement is performed.

    Returns:
        A list of words.
    """
    with tf.gfile.GFile(filename, "r") as f:
        if Py3:
            if newline_token is None:
                return f.read().split()
            else:
                return f.read().replace("\n", newline_token).split()
        else:
            if newline_token is None:
                return f.read().decode("utf-8").split()
            else:
                return (f.read().decode("utf-8")
                        .replace("\n", newline_token).split())


def make_vocab(filenames, max_vocab_size=-1,
               newline_token=None, return_type="list"):
    """Builds vocab of the files.

    Args:
        filenames (str): A (list of) files.
        max_vocab_size (int): Maximum size of the vocabulary. Low frequency
            words that exceeding the limit will be discarded.
            Set to `-1` (default) if no truncation is wanted.
        newline_token (str): The token to replace the original newline
            token `\n`. For example, `newline_token=tx.data.SpecialTokens.EOS`.
            If `None`, no replacement is performed.
        return_type (str): Either "list" or "dict". If "list" (default), this
            function returns a list of words sorted by frequency. If "dict",
            this function returns a dict mapping words to their index sorted
            by frequency.

    Returns:
        A list or dict.
    """
    if not isinstance(filenames, (list, tuple)):
        filenames = [filenames]

    words = []
    for fn in filenames:
        words += read_words(fn, newline_token=newline_token)

    counter = collections.Counter(words)
    count_pairs = sorted(counter.items(), key=lambda x: (-x[1], x[0]))

    words, _ = list(zip(*count_pairs))
    if max_vocab_size >= 0:
        words = words[:max_vocab_size]

    if return_type == "list":
        return words
    elif return_type == "dict":
        word_to_id = dict(zip(words, range(len(words))))
        return word_to_id
    else:
        raise ValueError("Unknown return_type: {}".format(return_type))


def count_file_lines(filenames):
    """Counts the number of lines in the file(s).
    """
    def _count_lines(fn):
        with open(fn, 'rb') as f:
            i = -1
            for i, _ in enumerate(f):
                pass
            return i + 1

    if not isinstance(filenames, (list, tuple)):
        filenames = [filenames]
    num_lines = np.sum([_count_lines(fn) for fn in filenames])
    return num_lines




