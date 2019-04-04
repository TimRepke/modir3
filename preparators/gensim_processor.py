from gensim.parsing import preprocessing as pp
from gensim import utils
import os
from abc import ABC, abstractmethod
from gensim.models.doc2vec import TaggedDocument, Doc2Vec
import ujson as json
import logging


class TaggedLineDocument(object):
    """Iterate over a file that contains sentences: one line = :class:`~gensim.models.doc2vec.TaggedDocument` object.

    Words are expected to be already preprocessed and separated by whitespace. Document tags are constructed
    automatically from the document line number (each document gets a unique integer tag).

    """

    def __init__(self, source, contains_id):
        """

        Parameters
        ----------
        source : string or a file-like object
            Path to the file on disk, or an already-open file object (must support `seek(0)`).

        """
        self.source = source
        self.contains_id = contains_id

    def _line2tagged_doc(self, line, item_no):
        if self.contains_id:
            try:
                line_parts = line.split('\t')
                item_no = line_parts[0]
                line = line_parts[1]
            except KeyError:
                pass
        return TaggedDocument(utils.to_unicode(line).split(), [item_no])

    def __iter__(self):
        """Iterate through the lines in the source.

        Yields
        ------
        :class:`~gensim.models.doc2vec.TaggedDocument`
            Document from `source` specified in the constructor.

        """
        try:
            # Assume it is a file-like object and try treating it as such
            # Things that don't have seek will trigger an exception
            self.source.seek(0)
            for item_no, line in enumerate(self.source):
                yield self._line2tagged_doc(line, item_no)
        except AttributeError:
            # If it didn't work like a file, use it as a string filename
            with utils.smart_open(self.source) as fin:
                for item_no, line in enumerate(fin):
                    yield self._line2tagged_doc(line, item_no)


class GensimProcessor(ABC):
    FILTER_FUNCS = [
        lambda s: s.lower(),
        pp.strip_tags,
        pp.strip_punctuation,
        pp.strip_multiple_whitespaces,
        pp.strip_numeric,
        pp.remove_stopwords,
        lambda s: pp.strip_short(s, 3),
        # pp.stem_text,
        pp.strip_non_alphanum,
        lambda s: s.strip()
    ]
    INFER_EPOCHS = 5
    D2V_KEY = 'd2v'
    TEXT_KEY = 'text'
    NORMED_TEXT_KEY = 'normed'
    TITLE_KEY = 'title'
    ID_KEY = 'id'

    def __init__(self, in_file, out_file, skip_empty=True):
        self.in_file = in_file

        self.out_file = out_file

        self.skip_empty = skip_empty
        self.include_id = False

        self._dimensionality = None
        self._count = None

        self.model = None

    @property
    def FILENAME_TXT(self):
        return f'{self.out_file}.gensim_txt'

    @property
    def FILENAME_JSON(self):
        return f'{self.out_file}.gensim_json'

    @property
    def FILENAME_MODEL(self):
        return f'{self.out_file}.gensim_model'

    def __len__(self):
        return self.get_count()

    @property
    def vectors(self):
        return self.get_vectors()

    @property
    def documents(self):
        return self.get_documents()

    @property
    def dimensionality(self):
        return self.get_dimensionality()

    @abstractmethod
    def _generate_docs(self):
        raise NotImplementedError

    def is_prepared(self):
        return os.path.isfile(self.FILENAME_JSON) and \
               os.path.isfile(self.FILENAME_TXT)

    def is_trained(self):
        return os.path.isfile(self.FILENAME_MODEL)

    def is_applied(self):
        return os.path.isfile(self.out_file)

    def _get_text(self, doc):
        return doc[self.TEXT_KEY]

    def _norm_text(self, text):
        s = utils.to_unicode(text)
        for func in self.FILTER_FUNCS:
            s = func(s)
        return s

    def _get_normed_text(self, doc):
        if self.NORMED_TEXT_KEY in doc:
            return doc[self.NORMED_TEXT_KEY]
        return self._norm_text(self._get_text(doc))

    def prepare(self):
        with open(self.FILENAME_JSON, 'w') as f_json, \
                open(self.FILENAME_TXT, 'w') as f_txt:
            for doc in self._generate_docs():
                txt = self._get_normed_text(doc)
                if not self.skip_empty or len(txt) > 0:
                    doc[self.NORMED_TEXT_KEY] = txt
                    f_txt.write(txt + '\n')
                    f_json.write(json.dumps(doc) + '\n')

    def train(self, min_count, max_vocab_size, vector_size, epochs, workers, verbosity=False):
        """

        Parameters
        ----------
        min_count
           see argparse --d2v-min-count
        max_vocab_size
           see argparse --d2v-max-vocab
        vector_size
           see argparse --d2v-size
        epochs
           see argparse --d2v-epochs
        workers
           see argparse --d2v-workers
        verbosity
           see argparse --gensim-logging
        """
        if not os.path.isfile(self.FILENAME_TXT):
            raise FileNotFoundError('Missing TaggedLineDocument file. Make sure to run prepare() first!')

        docs = TaggedLineDocument(self.FILENAME_TXT, contains_id=self.include_id)
        if verbosity:
            logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
        model = Doc2Vec(documents=docs, min_count=min_count, max_vocab_size=max_vocab_size,
                        vector_size=vector_size, epochs=epochs, workers=workers)
        model.save(self.FILENAME_MODEL)
        self._dimensionality = vector_size

    def apply(self, allow_infer):
        if not os.path.isfile(self.FILENAME_JSON) or not os.path.isfile(self.FILENAME_MODEL):
            raise FileNotFoundError('Missing TaggedLineDocument file. Make sure to run train() first!')

        stats = {'infer': 0, 'lookup': 0, 'skip': 0}
        with open(self.FILENAME_JSON, 'r') as f_in, \
                open(self.out_file, 'w') as f_out:
            model = Doc2Vec.load(self.FILENAME_MODEL)

            for i, line in enumerate(f_in):
                doc = json.loads(line)
                vector = None
                try:
                    vector = model.docvecs[i]
                    stats['lookup'] += 1
                except KeyError:
                    if allow_infer:
                        td = TaggedDocument(self._get_normed_text(doc).split(), [i])
                        vector = model.infer_vector(td.words, epochs=self.INFER_EPOCHS)
                        stats['infer'] += 1
                if vector is not None:
                    doc[self.D2V_KEY] = vector.tolist()
                    f_out.write(json.dumps(doc) + '\n')
                else:
                    stats['skip'] += 1
        print(f'Allied model to documents: did {stats["lookup"]} lookups, '
              f'{stats["infer"]} inferrals, and skipped {stats["skip"]}!')

    def get_documents(self):
        if not os.path.isfile(self.out_file):
            raise FileNotFoundError('Missing intermediate files. Make sure to run apply() first!')

        with open(self.out_file, 'r') as f_out:
            for line in f_out:
                doc = json.loads(line)
                yield doc

    def get_vectors(self):
        for doc in self.get_documents():
            yield doc[self.D2V_KEY]

    def get_vectors_batched(self, batch_size):
        batch = []
        i = 0
        for vector in self.get_vectors():
            batch.append(vector)
            i += 1
            if i > batch_size:
                yield batch
                batch = []
                i = 0
        if i > 0:
            yield batch

    def get_count(self):
        if self._count is None:
            i = 0
            for _ in self.get_vectors():
                i += 1
            self._count = i
        return self._count

    def get_dimensionality(self):
        if self._dimensionality is None:
            self._dimensionality = len(next(iter(self.get_vectors())))
        return self._dimensionality
