"""
preprocessing text data. Generally it's to generate plain text vocab file,
truncate sequence by length, generate the preprocessed dataset.
"""
from __future__ import unicode_literals
import collections
import io
import re
import json
import os
import numpy as np
import pickle

#pylint:disable=invalid-name

from config import get_preprocess_args
split_pattern = re.compile(r'([.,!?"\':;)(])')
digit_pattern = re.compile(r'\d')
Special_Seq = collections.namedtuple('Special_Seq', \
    ['PAD', 'BOS', 'EOS', 'UNK'])
Vocab_Pad = Special_Seq(PAD=0, BOS=1, EOS=2, UNK=3)

def split_sentence(s, tok=False):
    """split sentence with some segmentation rules."""
    if tok:
        s = s.lower()
        s = s.replace('\u2019', "'")
        s = digit_pattern.sub('0', s)
    words = []
    for word in s.split():
        if tok:
            words.extend(split_pattern.split(word))
        else:
            words.append(word)
    words = [w for w in words if w]
    return words


def open_file(path):
    """more robust open function"""
    return io.open(path, encoding='utf-8', errors='ignore')

def read_file(path, tok=False):
    """a generator to generate each line of file."""
    with open_file(path) as f:
        for line in f.readlines():
            words = split_sentence(line.strip(), tok)
            yield words


def count_words(path, max_vocab_size=40000, tok=False):
    """count all words in the corpus and output a counter"""
    counts = collections.Counter()
    for words in read_file(path, tok):
        for word in words:
            counts[word] += 1

    vocab = [word for (word, _) in counts.most_common(max_vocab_size)]
    return vocab

def make_array(word_id, words):
    """generate id numpy array from plain text words."""
    ids = [word_id.get(word, Vocab_Pad.UNK) for word in words]
    return np.array(ids, 'i')

def make_dataset(path, w2id, tok=False):
    """generate dataset."""
    dataset, npy_dataset = [], []
    token_count, unknown_count = 0, 0
    for words in read_file(path, tok):
        array = make_array(w2id, words)
        npy_dataset.append(array)
        dataset.append(words)
        token_count += array.size
        unknown_count += (array == Vocab_Pad.UNK).sum()
    print('# of tokens:{}'.format(token_count))
    print('# of unknown {} {:.2}'.format(unknown_count,
                                         100. * unknown_count / token_count))
    return dataset, npy_dataset


if __name__ == "__main__":
    args = get_preprocess_args()

    print(json.dumps(args.__dict__, indent=4))

    #pylint:disable=no-member
    # Vocab Construction
    source_path = os.path.join(args.input_dir, args.source_train)
    target_path = os.path.join(args.input_dir, args.target_train)

    src_cntr = count_words(source_path, args.source_vocab, args.tok)
    trg_cntr = count_words(target_path, args.target_vocab, args.tok)
    all_words = sorted(list(set(src_cntr + trg_cntr)))

    vocab = ['<pad>', '<bos>', '<eos>', '<unk>'] + all_words

    w2id = {word: index for index, word in enumerate(vocab)}

    # Train Dataset
    source_data, source_npy = make_dataset(source_path, w2id, args.tok)
    target_data, target_npy = make_dataset(target_path, w2id, args.tok)
    assert len(source_data) == len(target_data)

    train_data = [(s, t) for s, t in zip(source_data, target_data)
                  if s and len(s) < args.max_seq_length
                  and t and len(t) < args.max_seq_length]
    train_npy = [(s, t) for s, t in zip(source_npy, target_npy)
                 if len(s) > 0 and len(s) < args.max_seq_length
                 and len(t) > 0 and len(t) < args.max_seq_length]
    assert len(train_data) == len(train_npy)

    # Display corpus statistics
    print("Vocab: {} with special tokens".format(len(vocab)))
    print('Original training data size: %d' % len(source_data))
    print('Filtered training data size: %d' % len(train_data))

    # Valid Dataset
    source_path = os.path.join(args.input_dir, args.source_valid)
    source_data, source_npy = make_dataset(source_path, w2id, args.tok)
    target_path = os.path.join(args.input_dir, args.target_valid)
    target_data, target_npy = make_dataset(target_path, w2id, args.tok)
    assert len(source_data) == len(target_data)

    valid_data = [(s, t) for s, t in zip(source_data, target_data)
                  if s and t]
    valid_npy = [(s, t) for s, t in zip(source_npy, target_npy)
                 if len(s) > 0 and len(t) > 0]
    assert len(valid_data) == len(valid_npy)
    print('Original dev data size: %d' % len(source_data))
    print('Filtered dev data size: %d' % len(valid_data))

    # Test Dataset
    source_path = os.path.join(args.input_dir, args.source_test)
    source_data, source_npy = make_dataset(source_path, w2id, args.tok)
    target_path = os.path.realpath(
        os.path.join(args.input_dir, args.target_test))
    target_data, target_npy = make_dataset(target_path, w2id, args.tok)
    assert len(source_data) == len(target_data)
    test_data = [(s, t) for s, t in zip(source_data, target_data)
                 if s and t]
    test_npy = [(s, t) for s, t in zip(source_npy, target_npy)
                if len(s)>0 and len(t)>0]
    print('Original test data size: %d' % len(source_data))
    print('Filtered test data size: %d' % len(test_data))
    id2w = {i: w for w, i in w2id.items()}
    # Save the dataset to numpy files
    train_src_output = os.path.join(args.input_dir, \
        args.save_data + 'train.' + args.src+ '.txt')
    train_tgt_output = os.path.join(args.input_dir, \
        args.save_data + 'train.' + args.tgt + '.txt')
    dev_src_output = os.path.join(args.input_dir, \
        args.save_data + 'dev.' + args.src+ '.txt')
    dev_tgt_output = os.path.join(args.input_dir, \
        args.save_data + 'dev.' + args.tgt+ '.txt')
    test_src_output = os.path.join(args.input_dir, \
        args.save_data + 'test.' + args.src+ '.txt')
    test_tgt_output = os.path.join(args.input_dir, \
        args.save_data + 'test.' + args.tgt + '.txt')

    np.save(os.path.join(args.input, args.save_data + 'train.npy'),
            train_npy)
    np.save(os.path.join(args.input, args.save_data + 'valid.npy'),
            valid_npy)
    np.save(os.path.join(args.input, args.save_data + 'test.npy'),
            test_npy)
    with open(os.path.join(args.input, args.save_data + 'vocab.pickle'), 'wb')\
        as f:
        pickle.dump(id2w, f, protocol=pickle.HIGHEST_PROTOCOL)

    with open(train_src_output, 'w+') as fsrc, \
        open(train_tgt_output, 'w+') as ftgt:
        for words in train_data:
            fsrc.write('{}\n'.format(' '.join(words[0])))
            ftgt.write('{}\n'.format(' '.join(words[1])))
    with open(dev_src_output, 'w+') as fsrc, \
        open(dev_tgt_output, 'w+') as ftgt:
        for words in valid_data:
            fsrc.write('{}\n'.format(' '.join(words[0])))
            ftgt.write('{}\n'.format(' '.join(words[1])))
    with open(test_src_output, 'w+') as fsrc, \
        open(test_tgt_output, 'w+') as ftgt:
        for words in test_data:
            fsrc.write('{}\n'.format(' '.join(words[0])))
            ftgt.write('{}\n'.format(' '.join(words[1])))
    with open(os.path.join(args.input_dir, \
            args.save_data + args.pre_encoding + '.vocab.text'), 'w+') as f:
        max_size = len(id2w)
        for idx in range(4, max_size):
            f.write('{}\n'.format(id2w[idx]))
