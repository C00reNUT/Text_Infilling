# This code was taken from Tensor2Tensor on 03/30/2018
# Usage: t2t-bleu --translation=my-wmt13.de --reference=wmt13_deen.de

# This also:
# Put compounds in ATAT format (comparable to papers like GNMT, ConvS2S).
# See https://nlp.stanford.edu/projects/nmt/ :
# 'Also, for historical reasons, we split compound words, e.g.,
#    "rich-text format" --> rich ##AT##-##AT## text format."'
# BLEU score will be similar to the one obtained using: mteval-v14.pl
# Note:compound splitting is not implemented in this module


# coding=utf-8
# Copyright 2018 The Tensor2Tensor Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""BLEU metric util used during eval for MT."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from argparse import ArgumentParser
import collections
import math
import re
import sys
import unicodedata

# Dependency imports

import numpy as np
import six
# pylint: disable=redefined-builtin
from six.moves import xrange
from six.moves import zip


# pylint: enable=redefined-builtin


def _get_ngrams(segment, max_order):
    """Extracts all n-grams upto a given maximum order from an input segment.

  Args:
    segment: text segment from which n-grams will be extracted.
    max_order: maximum length in tokens of the n-grams returned by this
        methods.

  Returns:
    The Counter containing all n-grams upto max_order in segment
    with a count of how many times each n-gram occurred.
  """
    ngram_counts = collections.Counter()
    for order in xrange(1, max_order + 1):
        for i in xrange(0, len(segment) - order + 1):
            ngram = tuple(segment[i:i + order])
            ngram_counts[ngram] += 1
    return ngram_counts


def compute_bleu(reference_corpus,
                 translation_corpus,
                 max_order=4,
                 use_bp=True):
    """Computes BLEU score of translated segments against references.

    Args:
        reference_corpus: list of references for each translation. Each
            reference should be tokenized into a list of tokens.
        translation_corpus: list of translations to score. Each translation
            should be tokenized into a list of tokens.
        max_order: Maximum n-gram order to use when computing BLEU score.
        use_bp: boolean, whether to apply brevity penalty.
    Returns:
        BLEU score.
    """

    reference_length = 0
    translation_length = 0
    bp = 1.0
    geo_mean = 0

    matches_by_order = [0] * max_order
    possible_matches_by_order = [0] * max_order
    precisions = []

    for (references, translations) in zip(reference_corpus, translation_corpus):
        reference_length += len(references)
        translation_length += len(translations)
        ref_ngram_counts = _get_ngrams(references, max_order)
        translation_ngram_counts = _get_ngrams(translations, max_order)

        overlap = dict((ngram,
                        min(count, translation_ngram_counts[ngram]))
                       for ngram, count in ref_ngram_counts.items())

        for ngram in overlap:
            matches_by_order[len(ngram) - 1] += overlap[ngram]
        for ngram in translation_ngram_counts:
            possible_matches_by_order[len(ngram) - 1] += \
                translation_ngram_counts[ngram]
    precisions = [0] * max_order
    smooth = 1.0
    for i in xrange(0, max_order):
        if possible_matches_by_order[i] > 0:
            precisions[i] = matches_by_order[i] / possible_matches_by_order[i]
            if matches_by_order[i] > 0:
                precisions[i] = matches_by_order[i] / \
                    possible_matches_by_order[i]
            else:
                smooth *= 2
                precisions[i] = 1.0 / (smooth * possible_matches_by_order[i])
        else:
            precisions[i] = 0.0

    if max(precisions) > 0:
        p_log_sum = sum(math.log(p) for p in precisions if p)
        geo_mean = math.exp(p_log_sum / max_order)

    if use_bp:
        ratio = translation_length / reference_length
        bp = math.exp(1 - 1. / ratio) if ratio < 1.0 else 1.0
    bleu = geo_mean * bp
    return np.float32(bleu)


class UnicodeRegex(object):
    """Ad-hoc hack to recognize all punctuation and symbols."""
    # pylint:disable=too-few-public-methods
    def __init__(self):
        punctuation = self.property_chars("P")
        self.nondigit_punct_re = re.compile(r"([^\d])([" + punctuation + r"])")
        self.punct_nondigit_re = re.compile(r"([" + punctuation + r"])([^\d])")
        self.symbol_re = re.compile("([" + self.property_chars("S") + "])")

    def property_chars(self, prefix):
        #pylint:disable=no-self-use
        return "".join(six.unichr(x) for x in range(sys.maxunicode) \
            if unicodedata.category(six.unichr(x)).startswith(prefix))


uregex = UnicodeRegex()


def bleu_tokenize(string):
    r"""Tokenize a string following the official BLEU implementation.

  See https://github.com/moses-smt/mosesdecoder/"
           "blob/master/scripts/generic/mteval-v14.pl#L954-L983
  In our case, the input string is expected to be just one line
  and no HTML entities de-escaping is needed.
  So we just tokenize on punctuation and symbols,
  except when a punctuation is preceded and followed by a digit
  (e.g. a comma/dot as a thousand/decimal separator).

  Note that a numer (e.g. a year) followed by a dot at the end of sentence
  is NOT tokenized,
  i.e. the dot stays with the number because `s/(\p{P})(\P{N})/ $1 $2/g`
  does not match this case (unless we add a space after each sentence).
  However, this error is already in the original mteval-v14.pl
  and we want to be consistent with it.

  Args:
    string: the input string

  Returns:
    a list of tokens
  """
    string = uregex.nondigit_punct_re.sub(r"\1 \2 ", string)
    string = uregex.punct_nondigit_re.sub(r" \1 \2", string)
    string = uregex.symbol_re.sub(r" \1 ", string)
    return string.split()


def bleu_wrapper(ref_filename, hyp_filename, case_sensitive=False):
    """Compute BLEU for two files (reference and hypothesis translation)."""
    ref_lines = open(ref_filename, 'rb').read().decode('utf-8').splitlines()
    hyp_lines = open(hyp_filename, 'rb').read().decode('utf-8').splitlines()
    assert len(ref_lines) == len(hyp_lines)
    if not case_sensitive:
        ref_lines = [x.lower() for x in ref_lines]
        hyp_lines = [x.lower() for x in hyp_lines]
    ref_tokens = [bleu_tokenize(x) for x in ref_lines]
    hyp_tokens = [bleu_tokenize(x) for x in hyp_lines]
    return compute_bleu(ref_tokens, hyp_tokens)


if __name__ == "__main__":
    parser = ArgumentParser(description='Compute BLEU score. \
        Usage: t2t-bleu --translation=my-wmt13.de --reference=wmt13_deen.de')

    parser.add_argument('--translation', type=str)
    parser.add_argument('--reference', type=str)
    args = parser.parse_args()

    bleu = 100 * bleu_wrapper(args.reference,
                              args.translation,
                              case_sensitive=False)
    print("BLEU_uncased = %6.2f" % bleu)
    bleu = 100 * bleu_wrapper(args.reference,
                              args.translation,
                              case_sensitive=True)
    print("BLEU_cased = %6.2f" % bleu)
