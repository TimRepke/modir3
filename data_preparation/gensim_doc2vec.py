from gensim.models.doc2vec import TaggedDocument, Doc2Vec
from gensim.utils import deprecated, smart_open, to_unicode
import ujson as json
from gensim.parsing import preprocessing as pp
from gensim import utils
from email import parser as ep
from datetime import datetime, timezone
import numpy as np
import re
import json
import argparse
import typing
import time
from tqdm import tqdm
import logging
from xml.sax.saxutils import unescape
from lxml import etree

FILTER_FUNCS = [
    lambda s: s.lower(),
    pp.strip_tags,
    pp.strip_punctuation,
    pp.strip_multiple_whitespaces,
    pp.strip_numeric,
    pp.remove_stopwords,
    lambda s: pp.strip_short(s, 3),
    # pp.stem_text,
    pp.strip_non_alphanum
]


def norm_text(text):
    s = utils.to_unicode(text)
    for func in FILTER_FUNCS:
        s = func(s)
    return s


def venue2community(venue: str) -> str:
    for community, venues in {
        'DB': ['VLDB', 'SIGMOD', 'ICDE', 'EDBT'],
        'ML': ['NIPS', 'AAAI', 'ICML', 'CAI'],
        'DM': ['KDD', 'ICDM', 'CIKM', 'WSDM'],
        'ComLing': ['EMNLP', 'ACL', 'CoNLL', 'COLING'],
        'CompVis': ['CVPR', 'ICCV', 'ICIP', 'SIGGRAPH', 'Computer Vision'],
        'HCI': ['CHI', 'IUI', 'UIST', 'CSCW', 'CogSci', 'Cognitive Science']
    }.items():
        for venue_ in venues:
            # if venue_.upper() in venue.upper():
            if venue_ in venue:
                return community
    return 'Other'


def prepare_aminer(filename, td_sink: typing.IO = None, json_sink: typing.IO = None, index_sink: typing.IO = None,
                   skip_empty=True):
    # index ---- index id of this paper
    # * ---- paper title
    # @ ---- authors (separated by semicolons)
    # o ---- affiliations (separated by semicolons, and each affiliation corresponds to an author in order)
    # t ---- year
    # c ---- publication venue
    # % ---- the id of references of this paper (there are multiple lines, with each indicating a reference)
    # ! ---- abstract
    with open(filename, 'r') as f:
        index = 0
        doc = {}
        for line in tqdm(f):
            line = line.strip()
            if len(line) == 0:
                if not skip_empty or len(doc.get('abstract', '')) > 0:
                    doc['index'] = index
                    doc['normed'] = norm_text(doc.get('abstract', ''))
                    if json_sink is not None:
                        json_sink.write(json.dumps(doc) + '\n')
                    if td_sink is not None:
                        td_sink.write(doc['normed'] + '\n')
                    if index_sink is not None:
                        index_sink.write(f"{doc['id']}\t{index}\n")
                    index += 1
                doc = {}
            else:
                if line[:6] == '#index':
                    doc['id'] = line[7:]
                elif line[:2] == '#*':
                    doc['title'] = line[3:]
                elif line[:2] == '#@':
                    doc['authors'] = line[3:].split(';')
                elif line[:2] == '#o':
                    doc['affiliations'] = line[3:].split(';')
                elif line[:2] == '#t':
                    doc['year'] = line[3:]
                elif line[:2] == '#c':
                    doc['venue'] = line[3:]
                elif line[:2] == '#%':
                    if 'references' not in doc:
                        doc['references'] = []
                    doc['references'].append(line[3:])
                elif line[:2] == '#!':
                    doc['abstract'] = line[3:]
        print(f'Wrote {index + 1} documents!')


def prepare_enron(graph_file, td_sink: typing.IO = None, json_sink: typing.IO = None, index_sink: typing.IO = None,
                  skip_empty=True, only_original=True, td_with_id=False):
    index = 0
    for event, elem in etree.iterparse(graph_file):
        if elem.text == 'email':
            parent = elem.getparent()
            try:
                doc = {
                    'id': int(parent.get('id')),
                    'is_original': True,
                    'text': ''
                }
                for sibling in parent:
                    if sibling.get('key') == 'text':
                        doc['text'] = unescape(sibling.text or '').strip()
                    elif sibling.get('key') == 'subject':
                        doc['subject'] = sibling.text
                    elif sibling.get('key') == 'sent':
                        doc['sent'] = sibling.text
                    elif sibling.get('key') == 'block_type':
                        doc['block_type'] = sibling.text
                    elif sibling.get('key') == 'labelV':
                        doc['is_original'] = sibling.text == 'email'
                    elif sibling.get('key') == 'original':
                        doc['original_id'] = int(sibling.text)
                    sibling.clear()
                parent.clear()
                if only_original and not doc['is_original']:
                    continue

                doc['normed'] = norm_text(doc['text'])
                if skip_empty and len(doc['normed']) < 1:
                    # TODO try fallback to duplicate if text empty?
                    continue

                if td_sink is not None:
                    prefix = (str(doc['id']) + '\t') if td_with_id else ''
                    td_sink.write(prefix + doc['normed'] + '\n')
                if index_sink is not None:
                    index_sink.write(f"{doc['id']}\t{index}\n")
                if json_sink is not None:
                    json_sink.write(json.dumps(doc) + '\n')
                index += 1
            except TypeError as e:
                if str(e) != "int() argument must be a string, a bytes-like object or a number, not 'NoneType'":
                    print(e)
            except AttributeError as e:
                print(e)
        elem.clear()
    print(f'Wrote {index + 1} documents!')


def prepare_s2(filename, td_sink: typing.IO = None, index_sink: typing.IO = None, venue_sink: typing.TextIO = None,
               skip_empty=True, filter_venue=False, td_with_id=False):
    with open(filename, 'r') as f:
        index = 0
        for line in tqdm(f):
            doc = json.loads(line)
            community = venue2community(doc['venue'] or doc['journalName'] or '')
            if filter_venue and community == 'Other':
                continue
            if not skip_empty or len(doc.get('paperAbstract', '')) > 0:
                prefix = (str(doc['id']) + '\t') if td_with_id else ''
                if td_sink is not None:
                    td_sink.write(prefix + norm_text(doc['paperAbstract']) + '\n')
                if index_sink is not None:
                    index_sink.write(f"{doc['id']}\t{index}\n")
                if venue_sink is not None:
                    venue_sink.write(f"{doc['id']}\t{community}\t{doc['venue'] or doc['journalName']}\n")
                index += 1
        print(f'Wrote {index + 1} documents!')


def prepare_news(filename, td_sink: typing.IO = None, index_sink: typing.IO = None, skip_empty=True, td_with_id=False):
    with open(filename, 'r') as f:
        index = 0
        for line in tqdm(f):
            doc = json.loads(line)
            if not skip_empty or len(doc.get('article', '')) > 0:
                prefix = (str(doc['url']) + '\t') if td_with_id else ''
                if td_sink is not None:
                    td_sink.write(prefix + norm_text(doc['article']) + '\n')
                if index_sink is not None:
                    index_sink.write(f"{doc['url']}\t{index}\n")
                index += 1
        print(f'Wrote {index + 1} documents!')


def prepare_mcc(filename, td_sink: typing.IO = None, index_sink: typing.IO = None, skip_empty=True, td_with_id=False):
    with open(filename, 'r') as f:
        index = 0
        for line in tqdm(f):
            doc = json.loads(line)
            if not skip_empty or len(doc.get('content', '')) > 0:
                prefix = (str(index) + '\t') if td_with_id else ''
                if td_sink is not None:
                    td_sink.write(prefix + norm_text(doc['content']) + '\n')
                if index_sink is not None:
                    index_sink.write(f"{index}\t{index}\n")
                index += 1
        print(f'Wrote {index + 1} documents!')


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


def train_d2v(model_file, documents, min_count, max_vocab_size, vector_size, epochs, workers, td_with_id):
    docs = TaggedLineDocument(documents, td_with_id)
    model = Doc2Vec(documents=docs, min_count=min_count, max_vocab_size=max_vocab_size,
                    vector_size=vector_size, epochs=epochs, workers=workers)
    model.save(model_file)


def apply_d2v(model_file, documents: typing.IO, target: typing.IO, allow_infer, int_key=False, str_key=False):
    model = Doc2Vec.load(model_file)
    inferrals = 0
    lookups = 0
    skipped = 0
    for i, line in tqdm(enumerate(documents)):

        doc = json.loads(line)
        vector = None
        try:
            key = doc.get('index', i)
            try:
                if int_key: key = int(key)
                if str_key: key = str(key)
            except ValueError:
                pass
            vector = model.docvecs[key]
            lookups += 1
        except KeyError:
            if allow_infer:
                td = TaggedDocument(doc['normed'].split(), [doc['id']])
                vector = model.infer_vector(td.words, epochs=5)
                inferrals += 1
        if vector is not None:
            doc['d2v'] = vector.tolist()
            if 'venue' in doc or 'journalName' in doc:
                doc['community'] = venue2community(doc.get('venue') or doc.get('journalName') or '')
            if 'normed' not in doc:
                doc['normed'] = norm_text(doc.get('paperAbstract', ''))
            target.write(json.dumps(doc) + '\n')
        else:
            skipped += 1
    print(f'Allied model to documents: did {lookups} lookups, {inferrals} inferrals, and skipped {skipped}!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-data', default="./data/aminer/AMiner-Paper.txt",
                        help='path to data folder or file with input data')
    parser.add_argument('--doc-index', type=argparse.FileType('rw'), required=False,
                        help='write/read document index to enum index here')
    parser.add_argument('--processor', choices=['aminer', 'enron', 's2', 'news', 'mcc'], required=False,
                        help='choose the kind of preprocessor')
    parser.add_argument('--processor-target', type=argparse.FileType('w'), required=False,
                        help='writing input for TaggedLineDocument here')
    parser.add_argument('--processor-venues', type=argparse.FileType('a'), required=False,
                        help='write the parsed venues and communities here (NOTE: appending!)')
    parser.add_argument('--processor-target-with-id', action='store_true',
                        help='prepend the document id in the tagged document file')
    parser.add_argument('--processor-clean-target', type=argparse.FileType('w'), required=False,
                        help='write json per line file here after parsing')
    parser.add_argument('--skip-empty-abstract', action='store_true',
                        help='set to true if you want to exclude papers without abstract')
    parser.add_argument('--only-communities', action='store_true',
                        help='set to true if you want to restrict papers to known set of venues')
    parser.add_argument('--only-original', action='store_true',
                        help='set this flag if enron should only consider original (non-duplicate) mails')
    parser.add_argument('--documents', type=argparse.FileType('r'),
                        help='source for TaggedLineDocument')
    parser.add_argument('--documents-in', type=argparse.FileType('r'),
                        help='source for json documents to apply d2v to')
    parser.add_argument('--documents-out', type=argparse.FileType('w'),
                        help='target for json documents with added d2v field')
    parser.add_argument('--model', required=False, type=str,
                        help='filename of Doc2Vec model')
    parser.add_argument('--d2v-mode', choices=['train', 'apply'], required=False,
                        help='choose whether you want to train or apply a model')
    parser.add_argument('--d2v-max-vocab', type=int, default=10000,
                        help='max size of doc2vec vocab')
    parser.add_argument('--d2v-min-count', type=int, default=2,
                        help='min number of occurrences of a word')
    parser.add_argument('--d2v-size', type=int, default=128,
                        help='size of document vectors')
    parser.add_argument('--d2v-epochs', type=int, default=100,
                        help='number of epochs to train')
    parser.add_argument('--d2v-workers', type=int, default=8,
                        help='number of gensim workers')
    parser.add_argument('--d2v-allow-infer', action='store_true',
                        help='allow to infer vector if lookup is not possible during doc2vec apply')
    parser.add_argument('--gensim-logging', action='store_true',
                        help='turn on gensim logging. to pipe into file, use 2> ')
    parser.add_argument('--key-as-int', action='store_true',
                        help='set this flat if you want the doctag keys as int')
    parser.add_argument('--key-as-str', action='store_true',
                        help='set this flat if you want the doctag keys as str')
    args = parser.parse_args()

    print('Started at', time.strftime("%Y-%m-%d %H:%M"))

    if args.processor is not None:
        if args.processor == 'aminer':
            print('Going to preprocess AMiner data')
            prepare_aminer(filename=args.raw_data,
                           td_sink=args.processor_target,
                           json_sink=args.processor_clean_target,
                           index_sink=args.doc_index,
                           skip_empty=args.skip_empty_abstract)
        elif args.processor == 'enron':
            prepare_enron(graph_file=args.raw_data,
                          td_sink=args.processor_target,
                          json_sink=args.processor_clean_target,
                          index_sink=args.doc_index,
                          skip_empty=args.skip_empty_abstract,
                          only_original=args.only_original,
                          td_with_id=args.processor_target_with_id)
        elif args.processor == 's2':
            prepare_s2(filename=args.raw_data,
                       td_sink=args.processor_target,
                       skip_empty=args.skip_empty_abstract,
                       filter_venue=args.only_communities,
                       td_with_id=args.processor_target_with_id,
                       venue_sink=args.processor_venues)
        elif args.processor == 'news':
            prepare_news(args.raw_data,
                         td_sink=args.processor_target,
                         index_sink=args.doc_index,
                         skip_empty=args.skip_empty_abstract,
                         td_with_id=args.processor_target_with_id)
        elif args.processor == 'mcc':
            prepare_mcc(args.raw_data,
                        td_sink=args.processor_target,
                        index_sink=args.doc_index,
                        skip_empty=args.skip_empty_abstract,
                        td_with_id=args.processor_target_with_id)
        else:
            raise NotImplementedError(f'{args.processor} preprocessor not implemented!')
    elif args.d2v_mode is not None:
        if args.gensim_logging:
            logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
        if args.d2v_mode == 'train':
            print('Going to train model')
            train_d2v(model_file=args.model, documents=args.documents, min_count=args.d2v_min_count,
                      max_vocab_size=args.d2v_max_vocab, vector_size=args.d2v_size, epochs=args.d2v_epochs,
                      workers=args.d2v_workers, td_with_id=args.processor_target_with_id)
        else:
            print('Going to apply model')
            apply_d2v(model_file=args.model, documents=args.documents_in, target=args.documents_out,
                      allow_infer=args.d2v_allow_infer, int_key=args.key_as_int, str_key=args.key_as_str)
    else:
        print('NO ACTION!')
    print('Done at', time.strftime("%Y-%m-%d %H:%M"))
