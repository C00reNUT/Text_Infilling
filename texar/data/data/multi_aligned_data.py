#
"""
Paired text data that consists of source text and target text.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import copy

import tensorflow as tf

from texar.hyperparams import HParams
from texar.utils import utils
from texar.utils.dtypes import is_str, is_callable
from texar.data.data.text_data_base import TextDataBase
from texar.data.data.scalar_data import ScalarData
from texar.data.data.mono_text_data import _default_mono_text_dataset_hparams
from texar.data.data.scalar_data import _default_scalar_dataset_hparams
from texar.data.data.mono_text_data import MonoTextData
from texar.data.data_utils import count_file_lines
from texar.data.data import dataset_utils as dsutils
from texar.data.vocabulary import Vocab, SpecialTokens
from texar.data.embedding import Embedding

# pylint: disable=invalid-name, arguments-differ, not-context-manager
# pylint: disable=protected-access

__all__ = [
    "_default_dataset_hparams",
    "MultiAlignedData"
]

class _DataTypes(object): # pylint: disable=no-init, too-few-public-methods
    """Enumeration of data types.
    """
    TEXT = "text"
    INT = "int"
    FLOAT = "float"

def _is_text_data(data_type):
    return data_type == _DataTypes.TEXT
def _is_scalar_data(data_type):
    return data_type == _DataTypes.INT or data_type == _DataTypes.FLOAT

def _default_dataset_hparams(data_type=None):
    """Returns hyperparameters of a dataset with default values.
    """
    # TODO(zhiting): add more docs
    if not data_type or _is_text_data(data_type):
        hparams = _default_mono_text_dataset_hparams()
        hparams.update({
            "data_type": _DataTypes.TEXT,
            "vocab_share_with": None,
            "embedding_init_share_with": None,
            "processing_share_with": None,
        })
    elif _is_scalar_data(data_type):
        hparams = _default_scalar_dataset_hparams()
    return hparams

# pylint: disable=too-many-instance-attributes
class MultiAlignedData(TextDataBase):
    """Data consists of multiple aligned parts.

    Args:
        hparams (dict): Hyperparameters. See :meth:`default_hparams` for the
            defaults.
    """
    def __init__(self, hparams):
        TextDataBase.__init__(self, hparams)
        # Defaultizes hparams of each dataset
        datasets_hparams = self._hparams.datasets
        defaultized_datasets_hparams = []
        for ds_hpms in datasets_hparams:
            data_type = ds_hpms.get("data_type", None)
            defaultized_ds_hpms = HParams(ds_hpms,
                                          _default_dataset_hparams(data_type))
            defaultized_datasets_hparams.append(defaultized_ds_hpms)
        self._hparams.datasets = defaultized_datasets_hparams

        with tf.name_scope(self.name, self.default_hparams()["name"]):
            self._make_data()

    @staticmethod
    def default_hparams():
        """Returns a dicitionary of default hyperparameters.
        """
        hparams = TextDataBase.default_hparams()
        hparams["name"] = "multi_aligned_data"
        hparams["datasets"] = [_default_dataset_hparams()]
        return hparams

    @staticmethod
    def _raise_sharing_error(err_data, shr_data, hparam_name):
        raise ValueError(
            "Must only share specifications with a preceding dataset. "
            "Dataset %d has '%s=%d'" % (err_data, hparam_name, shr_data))

    @staticmethod
    def make_vocab(hparams):
        """Makes a list of vocabs based on the hparams.

        Args:
            hparams (list): A list of dataset hyperparameters.

        Returns:
            A list of :class:`texar.data.Vocab` instances. Some instances
            may be the same objects if they are set to be shared and have
            the same other configs.
        """
        if not isinstance(hparams, (list, tuple)):
            hparams = [hparams]

        vocabs = []
        for i, hparams_i in enumerate(hparams):
            if not _is_text_data(hparams_i["data_type"]):
                vocabs.append(None)
                continue

            proc_shr = hparams_i["processing_share_with"]
            if proc_shr is not None:
                bos_token = hparams[proc_shr]["bos_token"]
                eos_token = hparams[proc_shr]["eos_token"]
            else:
                bos_token = hparams_i["bos_token"]
                eos_token = hparams_i["eos_token"]
            bos_token = utils.default_str(
                bos_token, SpecialTokens.BOS)
            eos_token = utils.default_str(
                eos_token, SpecialTokens.EOS)

            vocab_shr = hparams_i["vocab_share_with"]
            if vocab_shr is not None:
                if vocab_shr >= i:
                    MultiAlignedData._raise_sharing_error(
                        i, vocab_shr, "vocab_share_with")
                if not vocabs[vocab_shr]:
                    raise ValueError("Cannot share vocab with dataset %d which "
                                     "does not have a vocab." % vocab_shr)
                if bos_token == vocabs[vocab_shr].bos_token and \
                        eos_token == vocabs[vocab_shr].eos_token:
                    vocab = vocabs[vocab_shr]
                else:
                    vocab = Vocab(hparams[vocab_shr]["vocab_file"],
                                  bos_token=bos_token,
                                  eos_token=eos_token)
            else:
                vocab = Vocab(hparams_i["vocab_file"],
                              bos_token=bos_token,
                              eos_token=eos_token)
            vocabs.append(vocab)

        return vocabs

    @staticmethod
    def make_embedding(hparams, vocabs):
        """Optionally loads embeddings from files (if provided), and
        returns respective :class:`texar.data.Embedding` instances.
        """
        if not isinstance(hparams, (list, tuple)):
            hparams = [hparams]

        embs = []
        for i, hparams_i in enumerate(hparams):
            if not _is_text_data(hparams_i["data_type"]):
                embs.append(None)
                continue

            emb_shr = hparams_i["embedding_init_share_with"]
            if emb_shr is not None:
                if emb_shr >= i:
                    MultiAlignedData._raise_sharing_error(
                        i, emb_shr, "embedding_init_share_with")
                if not embs[emb_shr]:
                    raise ValueError("Cannot share embedding with dataset %d "
                                     "which does not have an embedding." %
                                     emb_shr)
                if emb_shr != hparams_i["vocab_share_with"]:
                    raise ValueError("'embedding_init_share_with' != "
                                     "vocab_share_with. embedding_init can "
                                     "be shared only when vocab is shared.")
                emb = embs[emb_shr]
            else:
                emb = None
                emb_file = hparams_i["embedding_init"]["file"]
                if emb_file and emb_file != "":
                    emb = Embedding(vocabs[i].token_to_id_map_py,
                                    hparams_i["embedding_init"])
            embs.append(emb)

        return embs

    def _make_dataset(self):
        datasets = []
        for _, hparams_i in enumerate(self._hparams.datasets):
            dtype = hparams_i.data_type
            if _is_text_data(dtype) or _is_scalar_data(dtype):
                dataset = tf.data.TextLineDataset(
                    hparams_i.files,
                    compression_type=hparams_i.compression_type)
                datasets.append(dataset)
            else:
                raise ValueError("Unknown data type: %s" % hparams_i.data_type)
        return tf.data.Dataset.zip(tuple(datasets))

    #@staticmethod
    #def _get_name_prefix(dataset_hparams):
    #    def _dtype_conflict(dtype_1, dtype_2):
    #        conflict = ((dtype_1 == dtype_2) or
    #                    (dtype_1 in {_DataTypes.INT, _DataTypes.FLOAT} and
    #                     dtype_2 in {_DataTypes.INT, _DataTypes.FLOAT}))
    #        return conflict

    #    name_prefix = [hpms["data_name"] for hpms in dataset_hparams]
    #    name_prefix_dict = {}
    #    for i, np in enumerate(name_prefix):
    #        ids = name_prefix_dict.get(np, [])
    #        for j in ids:
    #            if _dtype_conflict(dataset_hparams[j]["data_type"],
    #                               dataset_hparams[i]["data_type"]):
    #                raise ValueError(
    #                    "'data_name' of the datasets with compatible "
    #                    "data_types cannot be the same: %d-th dataset and "
    #                    "%d-th dataset have the same name '%s'" %
    #                    (i, j, name_prefix[i]))
    #        ids.append(i)
    #        name_prefix_dict[np] = ids
    #    return name_prefix

    @staticmethod
    def _get_name_prefix(dataset_hparams):
        name_prefix = [hpms["data_name"] for hpms in dataset_hparams]
        for i in range(1, len(name_prefix)):
            if name_prefix[i] in name_prefix[:i-1]:
                raise ValueError("Data name duplicated: %s" % name_prefix[i])
        return name_prefix

    @staticmethod
    def _make_processor(dataset_hparams, data_spec, name_prefix):
        processors = []
        for i, hparams_i in enumerate(dataset_hparams):
            data_spec_i = data_spec.get_ith_data_spec(i)

            data_type = hparams_i["data_type"]
            if _is_text_data(data_type):
                tgt_proc_hparams = hparams_i
                proc_shr = hparams_i["processing_share_with"]
                if proc_shr is not None:
                    tgt_proc_hparams = copy.copy(dataset_hparams[proc_shr])
                    try:
                        tgt_proc_hparams["variable_utterance"] = \
                                hparams_i["variable_utterance"]
                    except TypeError:
                        tgt_proc_hparams.variable_utterance = \
                                hparams_i["variable_utterance"]

                processor, data_spec_i = MonoTextData._make_processor(
                    tgt_proc_hparams, data_spec_i)
            elif _is_scalar_data(data_type):
                processor, data_spec_i = ScalarData._make_processor(
                    hparams_i, data_spec_i, name_prefix='')
            else:
                raise ValueError("Unsupported data type: %s" % data_type)

            processors.append(processor)
            data_spec.set_ith_data_spec(i, data_spec_i, len(dataset_hparams))

        tran_fn = dsutils.make_combined_transformation(
            processors, name_prefix=name_prefix)

        data_spec.add_spec(name_prefix=name_prefix)

        return tran_fn, data_spec

    @staticmethod
    def _make_length_filter(dataset_hparams, length_name, decoder):
        filter_fns = []
        for i, hpms in enumerate(dataset_hparams):
            if not _is_text_data(hpms["data_type"]):
                filter_fn = None
            else:
                filter_fn = MonoTextData._make_length_filter(
                    hpms, length_name[i], decoder[i])
            filter_fns.append(filter_fn)
        combined_filter_fn = dsutils._make_combined_filter_fn(filter_fns)
        return combined_filter_fn

    def _process_dataset(self, dataset, hparams, data_spec):
        name_prefix = self._get_name_prefix(hparams["datasets"])
        # pylint: disable=attribute-defined-outside-init
        self._name_to_id = {v:k for k, v in enumerate(name_prefix)}

        tran_fn, data_spec = self._make_processor(
            hparams["datasets"], data_spec, name_prefix)

        num_parallel_calls = hparams["num_parallel_calls"]
        dataset = dataset.map(
            lambda *args: tran_fn(dsutils.maybe_tuple(args)),
            num_parallel_calls=num_parallel_calls)

        # Filters by length
        def _get_length_name(i):
            if not _is_text_data(hparams["datasets"][i]["data_type"]):
                return None
            name = dsutils._connect_name(
                data_spec.name_prefix[i],
                data_spec.decoder[i].length_tensor_name)
            return name
        filter_fn = self._make_length_filter(
            hparams["datasets"],
            [_get_length_name(i) for i in range(len(hparams["datasets"]))],
            data_spec.decoder)
        if filter_fn:
            dataset = dataset.filter(filter_fn)

        # Truncates data count
        dataset = dataset.take(hparams["max_dataset_size"])

        return dataset, data_spec

    def _make_bucket_length_fn(self):
        length_fn = self._hparams.bucket_length_fn
        if not length_fn:
            # Uses the length of the first text data
            i = -1
            for i, hparams_i in enumerate(self._hparams.datasets):
                if _is_text_data(hparams_i["data_type"]):
                    break
            if i < 0:
                raise ValueError("Undefined `length_fn`.")
            length_fn = lambda x: x[self.length_name(i)]
        elif not is_callable(length_fn):
            # pylint: disable=redefined-variable-type
            length_fn = utils.get_function(length_fn, ["texar.custom"])
        return length_fn

    def _make_padded_shapes(self, dataset, decoders):
        padded_shapes = dataset.output_shapes
        for i, hparams_i in enumerate(self._hparams.datasets):
            if not _is_text_data(hparams_i["data_type"]):
                continue
            if not hparams_i["pad_to_max_seq_length"]:
                continue
            text_and_id_shapes = MonoTextData._make_padded_text_and_id_shapes(
                dataset, hparams_i, decoders[i],
                self.text_name(i), self.text_id_name(i))

            padded_shapes.update(text_and_id_shapes)

        return padded_shapes

    def _make_data(self):
        self._vocab = self.make_vocab(self._hparams.datasets)
        self._embedding = self.make_embedding(self._hparams.datasets,
                                              self._vocab)

        # Create dataset
        dataset = self._make_dataset()
        dataset, dataset_size = self._shuffle_dataset(
            dataset, self._hparams, self._hparams.datasets[0].files)
        self._dataset_size = dataset_size

        # Processing
        data_spec = dsutils._DataSpec(dataset=dataset,
                                      dataset_size=self._dataset_size,
                                      vocab=self._vocab,
                                      embedding=self._embedding)
        dataset, data_spec = self._process_dataset(
            dataset, self._hparams, data_spec)
        self._data_spec = data_spec
        self._decoder = data_spec.decoder

        # Batching
        length_fn = self._make_bucket_length_fn()
        padded_shapes = self._make_padded_shapes(dataset, self._decoder)
        dataset = self._make_batch(
            dataset, self._hparams, length_fn, padded_shapes)

        # Prefetching
        if self._hparams.prefetch_buffer_size > 0:
            dataset = dataset.prefetch(self._hparams.prefetch_buffer_size)

        self._dataset = dataset


    def list_items(self):
        """Returns the list of item names that the data can produce.

        Returns:
            A list of strings.
        """
        return list(self._dataset.output_types.keys())

    @property
    def dataset(self):
        """The dataset.
        """
        return self._dataset

    def dataset_size(self):
        """Returns the number of data instances in the dataset.

        Note that this is the total data count in the raw files, before any
        filtering and truncation.
        """
        if not self._dataset_size:
            # pylint: disable=attribute-defined-outside-init
            self._dataset_size = count_file_lines(
                self._hparams.datasets[0].files)
        return self._dataset_size

    def _maybe_name_to_id(self, name_or_id):
        if is_str(name_or_id):
            if name_or_id not in self._name_to_id:
                raise ValueError("Unknown data name: {}".format(name_or_id))
            return self._name_to_id[name_or_id]
        return name_or_id

    def vocab(self, name_or_id):
        """Returns the :class:`~texar.data.Vocab` of text dataset by its name
        or id. `None` if the dataset is not of text type.

        Args:
            name_or_id (str or int): Data name or the index of text dataset.
        """
        i = self._maybe_name_to_id(name_or_id)
        return self._vocab[i]

    def embedding_init_value(self, name_or_id):
        """Returns the `Tensor` of embedding init value of the
        dataset by its name or id. `None` if the dataset is not of text type.
        """
        i = self._maybe_name_to_id(name_or_id)
        return self._embedding[i]

    def text_name(self, name_or_id):
        """The name of text tensor of text dataset by its name or id. If the
        dataaet is not of text type, returns `None`.
        """
        i = self._maybe_name_to_id(name_or_id)
        if not _is_text_data(self._hparams.datasets[i]["data_type"]):
            return None
        name = dsutils._connect_name(
            self._data_spec.name_prefix[i],
            self._data_spec.decoder[i].text_tensor_name)
        return name

    def length_name(self, name_or_id):
        """The name of length tensor of text dataset by its name or id. If the
        dataset is not of text type, returns `None`.
        """
        i = self._maybe_name_to_id(name_or_id)
        if not _is_text_data(self._hparams.datasets[i]["data_type"]):
            return None
        name = dsutils._connect_name(
            self._data_spec.name_prefix[i],
            self._data_spec.decoder[i].length_tensor_name)
        return name

    def text_id_name(self, name_or_id):
        """The name of length tensor of text dataset by its name or id. If the
        dataset is not of text type, returns `None`.
        """
        i = self._maybe_name_to_id(name_or_id)
        if not _is_text_data(self._hparams.datasets[i]["data_type"]):
            return None
        name = dsutils._connect_name(
            self._data_spec.name_prefix[i],
            self._data_spec.decoder[i].text_id_tensor_name)
        return name

    def utterance_cnt_name(self, name_or_id):
        """The name of utterance count tensor of text dataset by its name or id.
        If the dataset is not variable utterance text data, returns `None`.
        """
        i = self._maybe_name_to_id(name_or_id)
        if not _is_text_data(self._hparams.datasets[i]["data_type"]) or \
                not self._hparams.datasets[i]["variable_utterance"]:
            return None
        name = dsutils._connect_name(
            self._data_spec.name_prefix[i],
            self._data_spec.decoder[i].utterance_cnt_tensor_name)
        return name

    @property
    def data_name(self, name_or_id):
        """The name of the data tensor of scalar dataset by its name or id..
        If the dataset is not a scalar data, returns `None`.
        """
        i = self._maybe_name_to_id(name_or_id)
        if not _is_scalar_data(self._hparams.datasets[i]["data_type"]):
            return None
        name = dsutils._connect_name(
            self._data_spec.name_prefix[i],
            self._data_spec.decoder[i].data_tensor_name)
        return name

