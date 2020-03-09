from ..gensim_processor import GensimProcessor
from ..hypergraph import HyperGraph
from ..export import ModirVisExport
from xml.sax.saxutils import unescape
from collections import defaultdict, Counter
from lxml import etree


class EnronGensimProcessor(GensimProcessor):
    def __init__(self, only_original, *args, skip_n=0, limit_n=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.only_original = only_original
        self.skip_n = skip_n
        self.limit_n = limit_n

    def _generate_docs(self):
        index = 0
        skip_index = 0
        for event, elem in etree.iterparse(self.in_file):
            if elem.text == 'email':
                parent = elem.getparent()
                if parent is None:
                    continue
                try:
                    doc = {
                        self.ID_KEY: int(parent.get('id')),
                        'is_original': True,
                        self.TEXT_KEY: ''
                    }
                    for sibling in parent:
                        if sibling is None:
                            continue
                        elif sibling.get('key') == 'text':
                            doc[self.TEXT_KEY] = unescape(sibling.text or '').strip()
                            # TODO try fallback to duplicate if text empty?
                        elif sibling.get('key') == 'subject':
                            doc[self.TITLE_KEY] = sibling.text
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

                    # skip non-original mails
                    if self.only_original and not doc['is_original']:
                        elem.clear()
                        continue

                    # skip empty mails
                    if self.skip_empty and len(doc[self.TEXT_KEY]) == 0:
                        elem.clear()
                        continue

                    # skip N initial mails
                    if skip_index < self.skip_n:
                        elem.clear()
                        skip_index += 1
                        continue

                    # limit to N mails
                    if self.limit_n is not None and index > self.limit_n:
                        elem.clear()
                        break

                    index += 1
                    yield doc
                except TypeError as e:
                    if str(e) != "int() argument must be a string, a bytes-like object or a number, not 'NoneType'":
                        print(e)
                except AttributeError as e:
                    print(e)
            elem.clear()
        print(f'Yielded {index + 1} documents!')


class EnronHyperGraph(HyperGraph):

    def __init__(self, only_original, *args, min_num_mails=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.only_original = only_original
        self.min_num_mails = min_num_mails if min_num_mails is not None else 1

    def _get_doc_index(self):
        id2idx = {}
        for i, doc in enumerate(self.gensim_processor.documents):
            id2idx[doc[self.gensim_processor.ID_KEY]] = i
        return id2idx

    def _get_people_index(self):
        people_index = {}
        for event, elem in etree.iterparse(self.gensim_processor.in_file):
            if elem.text == 'alias' and elem.get('key') == 'type':
                parent = elem.getparent()
                try:
                    alias = {}
                    for sibling in parent:
                        if sibling.get('key') == 'pID':
                            alias['pID'] = int(sibling.text)
                        elif sibling.get('key') == 'name':
                            alias['name'] = sibling.text
                        sibling.clear()
                    parent.clear()
                    if alias.get('pID', 0) < 5 or alias.get('pID', 0) == 244589 or len(alias) < 2:
                        elem.clear()
                        continue

                    if alias['pID'] not in people_index:
                        people_index[alias['pID']] = {
                            'idx': len(people_index),
                            'id': alias['pID'],
                            'aliases': set(),
                            'name': alias['name'],
                            'docs': [],
                            'nodes': []
                        }
                    people_index[alias['pID']]['aliases'].add(alias['name'])
                except TypeError as e:
                    if str(e) != "int() argument must be a string, a bytes-like object or a number, not 'NoneType'":
                        print(e)
                except AttributeError as e:
                    print(e)
            elem.clear()
        return people_index

    def _get_mail2people_index(self, doc_index, people_index):
        mail2people = {}
        for event, elem in etree.iterparse(self.gensim_processor.in_file):
            if elem.get('key') == 'labelE':
                parent = elem.getparent()
                try:
                    source = int(parent.get('source'))
                    target = int(parent.get('target'))
                    parent.clear()
                    if elem.text == 'recipient':
                        mail = source
                        person = target
                    elif elem.text == 'sender':
                        mail = target
                        person = source
                    else:
                        elem.clear()
                        continue
                    # if mail in doc_index:
                    #    print(person, (mail in doc_index), (person in people_index))
                    if mail in doc_index and person in people_index:
                        if mail not in mail2people:
                            mail2people[mail] = []
                        mail2people[mail].append(person)
                        people_index[person]['docs'].append(doc_index[mail])
                except TypeError as e:
                    if str(e) != "int() argument must be a string, a bytes-like object or a number, not 'NoneType'":
                        print(e)
                except AttributeError as e:
                    print(e)
            elem.clear()
        return mail2people

    def _prepare_graph(self):
        print('  - (1/6) building doc index')
        doc_index = self._get_doc_index()
        print(f'          loaded {len(doc_index)} docs')
        print('  - (2/6) building people index')
        people_index = self._get_people_index()
        print(f'          loaded {len(people_index)} people')
        print('  - (3/6) building mail2people index, add mails to people index')
        mail2people_index = self._get_mail2people_index(doc_index, people_index)
        print(f'          loaded {len(mail2people_index)} mail2people index')

        print('  - (4/6) filter people index')
        del_keys = []
        for key, person in people_index.items():
            if len(person['docs']) < self.min_num_mails:
                del_keys.append(key)
        print(f'          prepared to remove {len(del_keys)} people')
        for key in del_keys:
            del people_index[key]
        print(f'          after filtering {len(people_index)} people left')

        print('  - (5/6) realign people index')
        for i, person in enumerate(people_index.values()):
            person['idx'] = i

        print('  - (6/6) enrich people index with nodes')
        for mail in mail2people_index.values():
            for pid1 in mail:
                for pid2 in mail:
                    if pid1 != pid2 and pid1 in people_index and pid2 in people_index:
                        people_index[pid1]['nodes'].append(people_index[pid2]['idx'])

        self.nodes = people_index
        print('  - prepared mail graph')


class EnronModirVisExport(ModirVisExport):

    def _get_node_sent(self, node_id):
        return []

    def _get_node_received(self, node_id):
        return []

    def _get_node_email(self, node_id):
        return ''

    def _get_node_org(self, node_id):
        return ''

    def _produce_docs(self):
        idx2id = {a['idx']: a['id'] for a in self.hypergraph.nodes.values()}
        for i, (vec, doc) in enumerate(zip(self.doc_pos, self.hypergraph.gensim_processor.documents)):
            yield {
                'id': str(i),
                'date': doc.get('sent', 1990),
                'text': doc.get('text', doc.get('title', 'NO_TEXT')),
                'category_a': '',
                'category_b': '',
                'keywords': Counter(
                    doc[self.hypergraph.gensim_processor.NORMED_TEXT_KEY].split()).most_common(100)[-40:],
                'vec': vec.tolist(),
                'nodes': [idx2id[aidx] for aidx in self.hypergraph.node2docs.getcol(i).tocsc().indices]
            }
