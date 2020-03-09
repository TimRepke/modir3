import re
import json
from tqdm import tqdm
from collections import Counter
from nltk import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from scipy.sparse import spmatrix, coo_matrix, lil_matrix, csr_matrix, dok_matrix, save_npz, load_npz
import numpy as np


def load_data():
    with open('../../data/news/coba_news_amb.json') as f:
        nodes_ = {}
        entities_ = []
        num_docs_ = 0
        for i, line in tqdm(enumerate(f)):
            doc = json.loads(line)
            num_docs_ += 1
            entity_index = {e['id']: e for e in doc['entities'] if e['type'] == 'ORGANIZATION'}
            for match in doc['matches']:
                if match['entity']:
                    eid = match['entity']['id']
                    if eid in entity_index:
                        if eid not in nodes_:
                            nodes_[eid] = {
                                'idx': len(nodes_),
                                'docs': [],
                                'nodes': [],
                                'id': eid,
                                'name': entity_index[eid]['name']
                            }
                        nodes_[eid]['docs'].append(i)
                        nodes_[eid]['nodes'] += entity_index.keys()
                        entities_.append(eid)

        return nodes_, entities_, num_docs_


def build_network(nodes_, num_docs_,
                  max_node_count=1000, min_node_count=100,
                  min_node2doc_count=1, min_node2node_count=10):
    nodes_filtered = {node['id']: node for node in nodes_.values()
                      if max_node_count > len(set(node['docs'])) > min_node_count and node['id'] not in [
                          'http://www.wikidata.org/entity/Q157617',  # CoBa
                          'http://www.wikidata.org/entity/Q19842103',  # Bloomberg
                          'http://www.wikidata.org/entity/Q13977',  # Bloomberg
                          'http://www.wikidata.org/entity/Q130879'  # Reuters
                      ]}
    nodes_index_ = {node['id']: i for i, node in enumerate(nodes_filtered.values())}
    nodes_index_rev_ = {v: k for k, v in nodes_index_.items()}
    print(f'  - nodes total: {len(nodes_)}, nodes filtered: {len(nodes_filtered)}')

    n2d = [(nodes_index_[node['id']], di) for node in nodes_filtered.values() for di in node['docs']]
    n2d = Counter(n2d)
    n2d = [(i, j, c) for (i, j), c in n2d.items() if c >= min_node2doc_count]
    node2docs = coo_matrix(([c for _, _, c in n2d],
                            ([i for i, _, _ in n2d],
                             [j for _, j, _ in n2d])),
                           shape=(len(nodes_filtered), num_docs_), dtype=np.int16)
    node2docs = node2docs.tocsr()
    print(f'  - non-zero node2docs: {node2docs.getnnz()}')

    n2n = [(nodes_index_[node['id']], nodes_index_[nid])
           for node in nodes_filtered.values()
           for nid in node['nodes']
           if nid in nodes_filtered]
    n2n = Counter(n2n)
    n2n = [(i, j, c) for (i, j), c in n2n.items() if c >= min_node2node_count]
    node2nodes_ = coo_matrix(([c for _, _, c in n2n],
                              ([i for i, _, _ in n2n],
                               [j for _, j, _ in n2n])),
                             shape=(len(nodes_filtered), len(nodes_filtered)), dtype=np.int16)
    node2nodes_ = node2nodes_.tocsr()
    print(f'  - non-zero node2nodes: {node2nodes_.getnnz()}')
    return node2nodes_, nodes_index_


def produce_json(node2nodes_, nodes_index_, nodes_):
    nodes_index_rev_ = {v: k for k, v in nodes_index.items()}
    obj_ = {
        'nodes': [{
            'id': node['id'],
            'name': node['name'],
            'idx': nodes_index_[node['id']],
            'count': len(nodes_[node['id']]['docs'])
        } for node in nodes_.values() if node['id'] in nodes_index_],
        'links': []
    }
    node2nodes_sym = (node2nodes_ + node2nodes_.T).toarray()
    for i in range(node2nodes_.shape[0]):
        for j in range(i + 1, node2nodes_.shape[1]):
            if node2nodes_sym[i][j].item() > 0:
                obj_['links'].append({
                    'source': nodes_index_rev_[i],
                    'target': nodes_index_rev_[j],
                    'value': node2nodes_sym[i][j].item()
                })
    return obj_


if __name__ == '__main__':
    nodes, entities, num_docs = load_data()
    print(len(entities))
    most_common = [(nodes[e]['name'], cnt) for e, cnt in Counter(entities).most_common()]
    print(len(most_common))
    print(most_common)
    node2nodes, nodes_index = build_network(nodes, num_docs,
                                            max_node_count=700,  # | 800
                                            min_node_count=30,  # 80 | 50
                                            min_node2doc_count=2,  # 3 | 3
                                            min_node2node_count=50)  # 80 | 50
    obj = produce_json(node2nodes, nodes_index, nodes)
    print(json.dumps(obj))

# {"source": "bloomberg", "title": "Commerzbank Wins Appeal on Bonus Claims by Employees of Dresdner Kleinwort",
#  "author": "KarinMatussek", "published": "2010-09-20T13:24:01Z",
#  "url": "http://www.bloomberg.com/news/2010-09-20/commerzbank-wins-bonus-appeals-\
#          case-by-dresdner-workers-in-frankfurt-court.html",
#  "article": "\n          \n          \n             Commerzbank AG , Germany\u2019s second-\nbiggest bank,
#              won dismissal of appeals cases filed by 14 former\nDresdner Kleinwort investment bank employees
#              over their bonuses.  \n The Frankfurt labor appeals court today backed a lower\ntribunal
#              which dismissed the suits last year. The employees seek\nbonuses for 2008 ranging from about 29,000
#              euros ($37,987) to\n450,000 euros. Commerzbank acquired Dresdner Bank AG last year\nand faces similar
#              ...",
#  "file_name": ".../2010-09-20/commerzbank-wins-bonus-appeals-case-by-dresdner-workers-in-frankfurt-cour",
#  "entities": [{"id": "http://www.wikidata.org/entity/Q750458", "name": "Capital market",
#                "url": "http://en.wikipedia.org/wiki/Capital%20market", "type": "CONCEPT", "salience": 0},
#               {"id": "http://www.wikidata.org/entity/Q1318295", "name": "Narrative",
#                "url": "http://en.wikipedia.org/wiki/Narrative", "type": "CONCEPT", "salience": 0},
#     ...],
#  "matches": [
#     {"charLength": 14, "charOffset": 36, "text": "Commerzbank AG",
#      "entity": {"id": "http://www.wikidata.org/entity/Q157617", "confidence": 1}},
#     {"charLength": 7, "charOffset": 53, "text": "Germany",
#      "entity": {"id": "http://www.wikidata.org/entity/Q183", "confidence": 0.15479280330178}},
#     {"charLength": 18, "charOffset": 135, "text": "Dresdner Kleinwort",
#      "entity": {"id": "http://www.wikidata.org/entity/Q884586", "confidence": 0.98985288501212}},
#     {"charLength": 9, "charOffset": 207, "text": "Frankfurt",
#      "entity": {"id": "http://www.wikidata.org/entity/Q1794", "confidence": 0.23043223107456}},
#     {"charLength": 11, "charOffset": 400, "text": "Commerzbank",
#      "entity": {"id": "http://www.wikidata.org/entity/Q157617", "confidence": 1}},
#     {"charLength": 16, "charOffset": 421, "text": "Dresdner Bank AG",
#      "entity": {"id": "http://www.wikidata.org/entity/Q1258529", "confidence": 0.98850718809836}},
#     ...], "language": "en"}
