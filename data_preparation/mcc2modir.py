from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE
import json
from collections import Counter
from tqdm import tqdm
import numpy as np

use_tf_idf = False
use_concepts = True
use_non_entities = False

TARGET = '/home/tim/Uni/HPI/workspace/landscape_d3/data/mcc.json'

with open('../../data/mcc/mcc_germany_amb_d2v.json', 'r') as f1:
    vectors = []
    companies = {}
    documents = []

    doc_cnt = 0
    tf_idf = []
    for doc_cnt, line in enumerate(tqdm(f1, desc='Extract docs and entities')):
        doc = json.loads(line)
        vectors.append(doc['d2v'])
        idx = {e['id']: e for e in doc['entities']}
        doc_names = []
        doc_companies = []
        for match in doc['matches']:
            if match['entity']:
                entity = idx[match['entity']['id']]
                if entity['name'] in ['Screenwriter', 'Quotation mark',
                                      'Bloomberg L.P.', 'Reuters', 'Bloomberg News']:
                    continue

                if entity['type'] == ['ORGANIZATION', 'LOCATION'][1]:
                    if entity['name'] not in companies:
                        companies[entity['name']] = []
                    companies[entity['name']].append(doc_cnt)
                    doc_companies.append(entity['name'])
                else:
                    doc_names.append(entity['name'])
            elif use_non_entities:
                doc_names.append(match['text'].replace('\n', ' '))

        doc_names_filtered = []
        for name in doc_names:
            skip_concept = False
            for exclude in ['percent', 'uefa', 'year', 'bank', 'discount', 'economy',
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
                            'august', 'december', 'nation', 'humor', 'funding', 'measure']:
                if exclude in name.lower():
                    skip_concept = True
                    break
            if not skip_concept:
                doc_names_filtered.append(name)

        doc_names = Counter(doc_names_filtered).most_common(40)
        if use_concepts:
            tf_idf.append('///'.join(doc_names_filtered))
        else:
            tf_idf.append(doc['article'])

        doc['entities'] = list(set(doc_companies))
        doc['keywords'] = doc_names

        documents.append(doc)
        doc_cnt += 1

    if use_tf_idf:
        if use_concepts:
            model = TfidfVectorizer(tokenizer=lambda d: d.split('///'), lowercase=False,
                                    min_df=0.001, max_df=0.8, max_features=30000)
        else:
            model = TfidfVectorizer(min_df=3, max_df=300, max_features=6000, ngram_range=(1, 2))
        tf_idf_vectors = model.fit_transform(tf_idf)
        vocab = {v: k for k, v in model.vocabulary_.items()}
        print('vocab size:', len(vocab))
        for i, tf_idf_vector in enumerate(tqdm(tf_idf_vectors, desc='tfidf keywords')):
            documents[i]['keywords'] = [vocab[key] for key in np.argsort(tf_idf_vector.toarray()[0])[-40:]]
            print([vocab[key] for key in np.argsort(tf_idf_vector.toarray()[0])[-40:]])
            print('--')

    vecs = TSNE(n_components=2, perplexity=20.0, early_exaggeration=12.0, learning_rate=200.0,
                n_iter=1000, verbose=1, method='barnes_hut', angle=0.5).fit_transform(vectors)
    print('')

    nodes = {}
    node_index = {}
    for i, (name, company_docs) in enumerate(tqdm(companies.items(), desc='node index')):
        company_vectors = [vecs[j] for j in company_docs]
        centre = np.mean(company_vectors, axis=0)
        nodes[str(i)] = {
            'id': str(i),
            'name': name,
            'vec': centre.tolist(),
            'weight': len(company_docs),
            'email': '',
            'org': '',
            'sent': [],
            'received': [],
            'docs': company_docs,
            'categories_a': [],
            'categories_b': []
        }
        node_index[name] = str(i)

    docs = {}
    category_a_index = {'cat': []}
    edges = []
    edge_index = {}
    KEYWORDS = 'wosarticle__de'
    for i, (doc, vec) in enumerate(tqdm(zip(documents, vecs), desc='doc and edge index')):
        docs[str(i)] = {
            'id': str(i),
            'date': doc['PY'],
            'text': doc['content'],
            'category_a': doc['ratings'],
            'category_b': '',
            'keywords': doc['keywords'],
            'vec': vec.tolist(),
            'nodes': [node_index[e] for e in doc['entities']]
        }
        # if doc['source'] not in category_a_index:
        #    category_a_index[doc['source']] = []
        # category_a_index[doc['source']].append(str(i))
        category_a_index['cat'].append(str(i))
        for k, name1 in enumerate(doc['entities']):
            for name2 in doc['entities'][k + 1:]:
                ent1 = nodes[node_index[name1]]
                ent2 = nodes[node_index[name2]]
                key = '|'.join(sorted([ent1['id'], ent2['id']]))

                if key not in edge_index:
                    edge_index[key] = len(edges)
                    edges.append({
                        'source': ent1['id'],
                        'target': ent2['id'],
                        'source_pos': ent1['vec'],
                        'target_pos': ent2['vec'],
                        'weight': 0,
                        'docs': []
                    })

                edges[edge_index[key]]['weight'] += 1
                edges[edge_index[key]]['docs'].append(str(i))

    edge_weights = [edge['weight'] for edge in edges]
    node_weights = [node['weight'] for node in nodes.values()]

    size = {
        'minx': np.min(vecs, axis=0).tolist()[0],
        'maxx': np.max(vecs, axis=0).tolist()[0],
        'miny': np.min(vecs, axis=0).tolist()[1],
        'maxy': np.max(vecs, axis=0).tolist()[1],
        'width': abs(np.min(vecs, axis=0).tolist()[0]) + abs(np.max(vecs, axis=0).tolist()[0]),
        'height': abs(np.min(vecs, axis=0).tolist()[1]) + abs(np.max(vecs, axis=0).tolist()[1]),
        'node_weights': {
            'min': min(node_weights),
            'max': max(node_weights),
            'range': max(node_weights) - min(node_weights)
        },
        'edge_weights': {
            'min': min(edge_weights),
            'max': max(edge_weights),
            'range': max(edge_weights) - min(edge_weights)
        },
        'word_grid': {
            'cols': 10,
            'rows': 10
        }
    }
    size['word_grid']['cell_height'] = size['height'] / size['word_grid']['rows']
    size['word_grid']['cell_width'] = size['width'] / size['word_grid']['cols']

    word_grid = []
    for i in range(size['word_grid']['cols']):
        word_grid.append([])
        for j in range(size['word_grid']['rows']):
            word_grid[i].append([])
    # word_grid = [[[]] * size['word_grid']['rows'] for _ in range(size['word_grid']['cols'])]
    for doc in docs.values():
        pos = doc['vec']
        col = min(size['word_grid']['rows'] - 1,
                  abs(int(abs(pos[1] - size['maxy']) // size['word_grid']['cell_height'])))
        row = min(size['word_grid']['cols'] - 1,
                  abs(int((pos[0] + abs(size['minx'])) // size['word_grid']['cell_width'])))
        if use_tf_idf:
            word_grid[col][row].extend(doc['keywords'])
        else:
            for keyword, count in doc['keywords']:
                word_grid[col][row].extend([keyword] * count)

    for i, col in enumerate(word_grid):
        for j, cell in enumerate(col):
            word_grid[i][j] = Counter(cell).most_common(20)

    modir = {
        'nodes': nodes,
        'edges': edges,
        'docs': docs,
        'category_a_index': category_a_index,
        # * category_a_index (dict)
        #   * keys: category (str)
        #   * values (list of doc IDs)
        'category_b_index': {},
        'word_grid': word_grid,
        # * word_grid (list (tr) of lists (td) of lists [keyword (str), count (int)])
        'size': size
    }

    with open(TARGET, 'w') as f3:
        f3.write(json.dumps(modir))
