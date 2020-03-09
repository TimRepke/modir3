from ..gensim_processor import GensimProcessor
from ..hypergraph import HyperGraph
from ..export import ModirVisExport
from collections import Counter
import json as json


class NewsGensimProcessor(GensimProcessor):

    def _generate_docs(self):
        with open(self.in_file, 'r') as f:
            index = 0
            for line in f:
                doc = json.loads(line)

                doc[self.ID_KEY] = doc['url']
                doc[self.TEXT_KEY] = doc.get('article', '')
                if self.TEXT_KEY != 'article':
                    del doc['article']

                yield doc
                index += 1
            print(f'Yielded {index + 1} documents!')


class NewsHyperGraph(HyperGraph):

    def _prepare_graph(self):
        for i, (vector, doc) in enumerate(zip(self.vectors, self.gensim_processor.documents)):
            # deal with node2node and node2doc
            entity_index = {e['id']: e for e in doc['entities'] if e['type'] == 'ORGANIZATION'}
            for match in doc['matches']:
                if match['entity']:
                    eid = match['entity']['id']

                    if eid in entity_index:
                        entity = self._assert_node(eid, values={
                            'docs': [],
                            'nodes': [],
                            'id': eid,
                            'name': entity_index[eid]['name'],
                            'type': entity_index[eid]['type'],
                            'count': 0
                        })
                        entity['docs'].append(i)
                        entity['nodes'] += [k for k in entity_index.keys() if k is not eid]
                        entity['count'] += 1

        print('  - iterated all docs')


class NewsModirVisExport(ModirVisExport):
    EXCLUDE_TOKENS = ['percent', 'uefa', 'year', 'bank', 'discount', 'economy',
                      'stock', 'bond', 'states', 'frankfurt', 'growth', 'germany',
                      'europe', 'london', 'currency', 'price', 'loan', 'barrel',
                      'share', 'sales', 'week', 'debt', 'economics', 'person',
                      'child', 'power', 'weather', 'god', 'data', 'yesterday',
                      'reporter', 'gambling', 'greece', 'contract', 'future',
                      'credit', 'metal', 'profit', 'business', 'court', 'tonne', 'security',
                      'swiss', 'conductor', 'month', 'problem', 'private', 'probab', 'cent',
                      'prize', 'price', 'demand', 'cricket', 'record', 'hungary', 'king',
                      'base', 'note', 'government', 'polish', 'people', 'analyst', 'maize',
                      'sterling', 'estimation', '(', 'budapest', 'time', 'depress',
                      'asset', 'military', 'academic', 'china', 'company', 'risk',
                      'chairman', 'survey', 'june', 'deal', 'day', 'war', 'september',
                      'august', 'december', 'nation', 'humor', 'funding', 'measure',
                      'quotation', 'investor', 'capital', 'release', 'screen',
                      'financial']

    def _get_node_sent(self, node_id):
        return []

    def _get_node_received(self, node_id):
        return []

    def _get_node_email(self, node_id):
        return ''

    def _get_node_org(self, node_id):
        return ''

    def _is_blocked(self, token):
        for exclude in self.EXCLUDE_TOKENS:
            if exclude in token.lower():
                return True
        return False

    def _produce_docs(self):
        for i, (vec, doc) in enumerate(zip(self.doc_pos, self.hypergraph.gensim_processor.documents)):
            idx = {e['id']: e for e in doc['entities']}
            nodes = set()
            keywords = []
            for match in doc['matches']:
                if match['entity']:
                    eid = match['entity']['id']
                    if eid in self.hypergraph.nodes:
                        nodes.add(eid)
                    elif not self._is_blocked(idx[eid]['name']):
                        keywords.append(idx[eid]['name'])
                elif not self._is_blocked(match['text']):
                    keywords.append(match['text'].replace('\n', ' '))

            yield {
                'id': str(i),
                'date': doc['published'],
                'text': doc['text'],
                'category_a': doc['source'],
                'category_b': '',
                'keywords': Counter(keywords).most_common(40),
                'vec': vec.tolist(),
                'nodes': list(nodes)
            }
