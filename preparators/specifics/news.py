from ..gensim_processor import GensimProcessor
from ..hypergraph import HyperGraph
import ujson as json
import numpy as np


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
            entity_index = {e['id']: e for e in doc['entities']}
            entity_ids = []
            for match in doc['matches']:
                if match['entity']:
                    eid = match['entity']['id']

                    if entity_index[eid]['type'] == 'ORGANIZATION':
                        entity = self._assert_node(eid, values={
                            'id': eid,
                            'name': entity_index[eid]['name'],
                            'type': entity_index[eid]['type']
                        })
                        entity['docs'].append(i)
                        entity_ids.append(eid)

            entity_ids = set(entity_ids)
            idxs = [self.nodes[eid]['idx'] for eid in entity_ids]
            for j, eid in enumerate(entity_ids):
                self.nodes[eid]['nodes'] += idxs[:j] + idxs[j + 1:]
        print('  - iterated all docs')
