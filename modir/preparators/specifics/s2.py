from .papers import PaperGensimProcessor
from ..gensim_processor import GensimProcessor
from ..hypergraph import HyperGraph
from ..export import ModirVisExport
from collections import Counter
import json as json
import numpy as np


class S2GensimProcessor(PaperGensimProcessor, GensimProcessor):

    def _generate_docs(self):
        with open(self.in_file, 'r') as f:
            index = 0
            for line in f:
                doc = json.loads(line)

                venue = doc['venue'] or doc['journalName'] or ''
                community = self._venue2community(venue)

                doc[self.VENUE_KEY] = venue
                doc[self.COMMUNITY_KEY] = community

                if self.filter_venue and community == self.UNDEFINED_COMMUNITY:
                    continue

                txt = doc.get('paperAbstract', '')
                del doc['paperAbstract']
                doc[self.TEXT_KEY] = txt
                index += 1
                yield doc
            print(f'Yielded {index + 1} documents!')


class S2HyperGraph(HyperGraph):

    def _prepare_graph(self):
        for i, (vector, doc) in enumerate(zip(self.vectors, self.gensim_processor.documents)):
            # deal with node2node and node2doc
            author_ids = []
            for doc_author in doc['authors']:
                aid = doc_author['ids'][0] if len(doc_author['ids']) > 0 else doc_author['name']
                author = self._assert_node(aid, values={
                    'id': aid,
                    'name': doc_author['name']
                })
                author['docs'].append(i)
                author_ids.append(aid)

            author_ids = set(author_ids)
            idxs = [self.nodes[aid]['idx'] for aid in author_ids]
            for j, aid in enumerate(author_ids):
                self.nodes[aid]['nodes'] += idxs[:j] + idxs[j + 1:]
        print('  - iterated all docs')


class S2ModirVisExport(ModirVisExport):

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
            cat_a = doc[self.hypergraph.gensim_processor.VENUE_KEY]
            cat_b = doc[self.hypergraph.gensim_processor.COMMUNITY_KEY]

            yield {
                'id': str(i),
                'date': doc.get('year', 1990),
                'text': doc.get('text', doc.get('title', 'None')),
                'category_a': cat_a,
                'category_b': cat_b,
                'keywords': [[e, 1] for e in doc.get('entities', [])],
                'vec': vec.tolist(),
                'nodes': [idx2id[aidx] for aidx in self.hypergraph.node2docs.getcol(i).tocsc().indices]
            }
