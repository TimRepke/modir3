import re
import colorsys
import json as json
from xml.sax.saxutils import escape as xml_escape
from tqdm import tqdm
import numpy as np
from collections import Counter
from abc import ABC, abstractmethod


def save_str(string):
    if not string:
        return 'XXX'
    return re.sub(r'[^A-Za-z0-9 ]', '', string)


def escape(d):
    s = str(d)
    return xml_escape(s)


def svg_scatter(xy, categories=None, ids=None,
                canvas_height=100, canvas_width=100, opacity=1.0, doc_as_circle=False, dotsize=2):
    minx, maxx, miny, maxy = xy[0][0], xy[0][0], xy[0][1], xy[0][1]
    for xyi in xy:
        if minx > xyi[0]:
            minx = xyi[0]
        if maxx < xyi[0]:
            maxx = xyi[0]
        if miny > xyi[1]:
            miny = xyi[1]
        if maxy < xyi[1]:
            maxy = xyi[1]
    width = abs(minx) + abs(maxx)
    height = abs(miny) + abs(maxy)
    category_map = {}
    if categories:
        for category in categories:
            category_map[save_str(category)] = (.0, .0, .0)
        for i, category in enumerate(category_map):
            category_map[category] = colorsys.hsv_to_rgb(i / len(category_map), 1.0, 1.0)

    svg = f'<svg viewBox="{-5} {-5} {canvas_width + 10} {canvas_height + 10}" ' \
        f'height="{canvas_height}" width="{canvas_width}" xmlns="http://www.w3.org/2000/svg">\n'

    for i, xyi in enumerate(xy):
        x = ((xyi[0] - minx) / width) * canvas_width
        y = (abs(xyi[1] - maxy) / height) * canvas_height
        if categories:
            colour = category_map[categories[i]]
        else:
            colour = colorsys.hsv_to_rgb(0.5, 1.0, 1.0)
        if opacity == 1. or opacity is None:
            colour = f'rgb({int(colour[0] * 255)}, {int(colour[1] * 255)}, {int(colour[2] * 255)})'
        else:
            colour = f'rgba({int(colour[0] * 255)}, {int(colour[1] * 255)}, {int(colour[2] * 255)}, {opacity})'
        if doc_as_circle:
            style = 'fill:none; stroke-width:5px; stroke:' + colour
        else:
            style = 'fill:' + colour
        doc_id = i if not ids else ids[i]
        label = 'none' if not categories else save_str(categories[i])
        svg += f'  <circle class="doc" cx="{x}" cy="{y}" r="{dotsize}" style="{style}" ' \
            f'id="doc_{doc_id}" label="{label}" />\n'

    svg += '</svg>'
    return svg


def make_svg(filename, embedding=None, vectors=None, idxs=None, ids=None, labels=None):
    print(f'Writing SVG to {filename}')
    if idxs is None:
        idxs = range(embedding.shape[0])
    if embedding is not None:
        vectors = [embedding[idx] for idx in idxs]
    svg = svg_scatter(vectors, categories=labels, ids=ids,
                      canvas_height=1000, canvas_width=1200, opacity=0.8, doc_as_circle=False, dotsize=5)
    with open(filename, 'w') as f:
        f.write(svg)


def make_graphml(target, target_full=None):
    graphml_header = """<?xml version="1.0" encoding="UTF-8"?>
    <graphml xmlns="http://graphml.graphdrawing.org/xmlns"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns
             http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">
      <key id="v_name" for="node" attr.name="name" attr.type="string"/>
      <key id="v_color" for="node" attr.name="__color" attr.type="string"/>
      <key id="v_size" for="node" attr.name="size" attr.type="string"/>
      <key id="v_type" for="node" attr.name="type" attr.type="string"/>
      <key id="v_author" for="node" attr.name="Author" attr.type="string"/>
      <key id="v_published" for="node" attr.name="Published" attr.type="string"/>
      <key id="v_outlet" for="node" attr.name="NewsOutlet" attr.type="string"/>
      <key id="v_title" for="node" attr.name="_title" attr.type="string"/>
      <key id="v_cover" for="node" attr.name="__cover" attr.type="string"/>
      <key id="v_url" for="node" attr.name="URL" attr.type="string"/>
      <key id="v_wikipedia" for="node" attr.name="Wikipedia" attr.type="string"/>
      <key id="v_wikidata" for="node" attr.name="WikiData" attr.type="string"/>
    
    
      <key id="e_color" for="edge" attr.name="__color" attr.type="string"/>
      <key id="e_size" for="edge" attr.name="size" attr.type="string"/>
      <key id="e_type" for="edge" attr.name="type" attr.type="string"/>
      <key id="e_snipped" for="edge" attr.name="_snippet" attr.type="string"/>
      <key id="e_file" for="edge" attr.name="file" attr.type="string"/>
      <graph>
    """

    graphml_footer = """
      </graph>
    </graphml>
    """

    entity_types = ['ORGANIZATION', 'PERSON', 'LOCATION']

    type_map = {
        'ORGANIZATION': 'Company',
        'PERSON': 'Person',
        'LOCATION': 'Location'
    }

    with open('../../data/mcc/mcc_germany_amb.json', 'r') as f1, \
            open('/home/tim/Uni/HPI/workspace/CLE/mcc_germany.graphml', 'w') as f2, \
            open('/home/tim/Uni/HPI/workspace/CLE/mcc_germany_articles.graphml', 'w') as f3:
        entities = {}
        documents = []

        f2.write(graphml_header)
        f3.write(graphml_header)
        edges = {}
        for doc_cnt, line in enumerate(tqdm(f1, desc='Extract docs and entities')):
            doc = json.loads(line)
            idx = {e['id']: e for e in doc['entities']}
            doc_entities = []
            for match in doc['matches']:
                if match['entity']:
                    entity = idx[match['entity']['id']]
                    if entity['name'] in ['Screenwriter', 'Quotation mark',
                                          'Bloomberg L.P.', 'Reuters', 'Bloomberg News']:
                        continue

                    if entity['type'] in entity_types:
                        if entity['name'] not in entities:
                            entities[entity['name']] = {
                                'name': entity['name'],
                                'url': entity['url'],
                                'type': entity['type'],
                                'wikidata': entity['id'],
                                'docs': []
                            }
                        entities[entity['name']]['docs'].append(doc_cnt)
                        doc_entities.append(entity['name'])

            doc['entities'] = list(set(doc_entities))

            for entity1 in doc['entities']:
                for entity2 in doc['entities']:
                    if entity1 != entity2:
                        key = '|'.join(sorted([entity1, entity2]))
                        if key not in edges:
                            edges[key] = {
                                'e1': entity1,
                                'e2': entity2,
                                'docs': []
                            }
                        edges[key]['docs'].append(doc_cnt)

            f3.write(f'<node id="n{doc_cnt}">\n'
                     # f'  <data key="v_name">{escape(doc["title"][:25])}</data>\n'
                     f'  <data key="v_type">Article</data>\n'
                     f'  <data key="v_size">1</data>\n'
                     f'  <data key="v_title">{escape(doc["title"])}</data>\n'
                     f'  <data key="v_published">{escape(doc["PY"])}</data>\n'
                     f'  <data key="v_author">{escape(doc["authors"])}</data>\n'
                     f'  <data key="v_rating">'
                     f'{escape(doc["rating_1"])} | {escape(doc["rating_2"])} | '
                     f'{escape(doc["rating_3"])} | {escape(doc["rating_39"])} | '
                     f'{escape(doc["rating_7"])} | {escape(doc["ratings"])}</data>\n'
                     f'  <data key="v_tags">{escape(",".join(doc["tags"]))}</data>\n'
                     f'  <data key="v_wos_de">{escape(",".join(doc["wosarticle__de"]))}</data>\n'
                     f'  <data key="v_wos_wc">{escape(",".join(doc["wosarticle__wc"]))}</data>\n'
                     '</node>\n')

            documents.append(doc)

        entity_offset = len(documents)
        for i, entity in enumerate(tqdm(entities.values(), desc='entity node iterator'), start=entity_offset):
            nid = f'n{i}'
            edocs = list(set(entity['docs']))
            entities[entity['name']]['id'] = nid
            edge = f'<node id="{nid}">\n' \
                f'  <data key="v_name">{escape(entity["name"])}</data>\n' \
                f'  <data key="v_type">{type_map[entity["type"]]}</data>\n' \
                f'  <data key="v_size">{len(edocs)}</data>\n' \
                f'  <data key="v_wikipedia">{entity["url"]}</data>\n' \
                f'  <data key="v_wikidata">{entity["wikidata"]}</data>\n' \
                '</node>\n'
            f2.write(edge)
            f3.write(edge)

        for i, doc in enumerate(tqdm(documents, desc='article-entity edges')):
            aid = f'n{i}'
            for entity in set(doc['entities']):
                eid = entities[entity]['id']
                f3.write(f'<edge source="{aid}" target="{eid}">\n'
                         '  <data key="e_type">appeared_in</data>\n'
                         '  <data key="e_size">1</data>\n'
                         '</edge>\n')

        for i, edge in enumerate(tqdm(edges.values(), desc='entity-entity edges')):
            e1 = entities[edge['e1']]
            e2 = entities[edge['e2']]
            ndocs = len(set(edge["docs"]))
            if ndocs > 10:
                edge_xml = f'<edge source="{e1["id"]}" target="{e2["id"]}">\n' \
                    '  <data key="e_type">is_related</data>\n' \
                    f'  <data key="e_size">{ndocs}</data>\n' \
                    '</edge>\n'
                f2.write(edge_xml)
                f3.write(edge_xml)

        f2.write(graphml_footer)
        f3.write(graphml_footer)


class ModirVisExport(ABC):

    def __init__(self, layout_file, hypergraph, file_name, word_grid_cols, word_grid_rows):
        self.layout_file = layout_file
        self.hypergraph = hypergraph
        self.word_grid_cols = word_grid_cols
        self.word_grid_rows = word_grid_rows
        self.file_name = file_name

        self.doc_pos = np.array([])
        self.node_idx2id = {}
        self.node_idx2id_orig = {}
        self.node_pos = {}

    @property
    def FILENAME_EXPORT(self):
        return f'{self.file_name}.modir.json'

    def _load_layout(self):
        positions = []
        with open(self.layout_file, 'r') as f:
            for line in f:
                positions.append([float(yi) for yi in line.split(',')])
            self.doc_pos = np.array(positions)

    def _compute_node_pos(self):
        # self.hypergraph.node2docs
        self.node_pos = {}
        self.node_idx2id = {}
        self.node_idx2id_orig = {}
        print(len(self.hypergraph.nodes))
        for node_id, node in self.hypergraph.nodes.items():
            doc_ids = self.hypergraph.node2docs.tocsr().getrow(node['idx'])
            # print(type(doc_ids))
            doc_pos = self.doc_pos[doc_ids.indices]
            if doc_ids.getnnz() > 0:
                self.node_pos[node_id] = doc_pos.sum(axis=0) / doc_ids.getnnz()
                self.node_idx2id_orig[node['idx_orig']] = node_id
                self.node_idx2id[node['idx']] = node_id

    def _get_sizes(self):
        vecs = self.doc_pos
        size = {
            'minx': np.min(vecs, axis=0).tolist()[0],
            'maxx': np.max(vecs, axis=0).tolist()[0],
            'miny': np.min(vecs, axis=0).tolist()[1],
            'maxy': np.max(vecs, axis=0).tolist()[1],
            'width': abs(np.min(vecs, axis=0).tolist()[0]) + abs(np.max(vecs, axis=0).tolist()[0]),
            'height': abs(np.min(vecs, axis=0).tolist()[1]) + abs(np.max(vecs, axis=0).tolist()[1]),
            'node_weights': {
                'min': self.hypergraph.node2docs.data.min().item(),
                'max': self.hypergraph.node2docs.max().item(),
                'range': (self.hypergraph.node2docs.max() - self.hypergraph.node2docs.data.min()).item()
            },
            'edge_weights': {
                'min': self.hypergraph.node2nodes.data.min().item(),
                'max': self.hypergraph.node2nodes.max().item(),
                'range': (self.hypergraph.node2nodes.max() - self.hypergraph.node2nodes.data.min()).item()
            },
            'word_grid': {
                'cols': self.word_grid_cols,
                'rows': self.word_grid_rows
            }
        }
        size['word_grid']['cell_height'] = size['height'] / size['word_grid']['rows']
        size['word_grid']['cell_width'] = size['width'] / size['word_grid']['cols']
        return size

    def _get_nodes(self):
        nodes = {}
        for node_id, node in self.hypergraph.nodes.items():
            docs = self.hypergraph.node2docs.tocsr().getrow(node['idx'])
            if docs.getnnz() > 0:
                nodes[node_id] = {
                    'id': str(node_id),
                    'name': node['name'],
                    'vec': self.node_pos[node_id].tolist(),
                    'weight': docs.getnnz(),  # len(node['docs']),
                    'email': self._get_node_email(node_id),
                    'org': self._get_node_org(node_id),
                    'sent': self._get_node_sent(node_id),
                    'received': self._get_node_received(node_id),
                    'docs': [f'{di}' for di in docs.indices],  # node['docs'],
                    'categories_a': [],
                    'categories_b': []
                }
        return nodes

    def _get_edges(self):
        edges = []
        for source_i, _ in enumerate(self.hypergraph.node2nodes):
            edge_list = self.hypergraph.node2nodes.getcol(source_i).T + self.hypergraph.node2nodes.getrow(source_i)
            for target_i, edge_weight in zip(edge_list.tocsr().indices, edge_list.data):
                if target_i < source_i:
                    continue
                try:
                    source_id = self.node_idx2id[source_i]
                    target_id = self.node_idx2id[target_i]
                    # if source_id == 'http://www.wikidata.org/entity/Q157617':
                    #    continue
                    edges.append({
                        'source': source_id,
                        'target': target_id,
                        'source_pos': self.node_pos[source_id].tolist(),
                        'target_pos': self.node_pos[target_id].tolist(),
                        'weight': edge_weight.item(),
                        'docs': list(set(self.hypergraph.node2docs[source_i].indices.tolist())
                                     .intersection(set(self.hypergraph.node2docs[target_i].indices.tolist())))
                    })
                except KeyError as e:
                    print(f'Missing document for {e}')
                    # print(type(source_i))
                    # print(self.node_idx2id)
                    # raise e
        print('          edges:', len(edges))
        return edges

    def _category_index(self, docs, key):
        index = {}
        for did, doc in docs.items():
            if doc[key] not in index:
                index[doc[key]] = []
            index[doc[key]].append(did)
        return index

    def _generate_wordgrid(self, size, docs):

        word_grid = []
        for i in range(size['word_grid']['cols']):
            word_grid.append([])
            for j in range(size['word_grid']['rows']):
                word_grid[i].append([])
        for doc in docs.values():
            pos = doc['vec']
            col = min(size['word_grid']['rows'] - 1,
                      abs(int(abs(pos[1] - size['maxy']) // size['word_grid']['cell_height'])))
            row = min(size['word_grid']['cols'] - 1,
                      abs(int((pos[0] + abs(size['minx'])) // size['word_grid']['cell_width'])))
            for keyword, count in doc['keywords']:
                word_grid[col][row].extend([keyword] * count)

        for i, col in enumerate(word_grid):
            for j, cell in enumerate(col):
                word_grid[i][j] = Counter(cell).most_common(20)
        return word_grid

    def write_export(self):

        self._load_layout()
        print('  - (1/7) loaded layout')
        self._compute_node_pos()
        print('  - (2/7) computed node positions')

        nodes = self._get_nodes()
        print('  - (3/7) gathered node information')
        edges = self._get_edges()
        print('  - (4/7) gathered edge information')
        docs = {doc['id']: doc for doc in self._produce_docs()}
        print('  - (5/7) built doc index')
        sizes = self._get_sizes()
        print('  - (6/7) calculated landscape sizes')
        word_grid = self._generate_wordgrid(sizes, docs)
        print('  - (7/7) created word grid')

        modir = {
            'nodes': nodes,
            'edges': edges,
            'docs': docs,
            'category_a_index': self._category_index(docs, 'category_a'),
            'category_b_index': self._category_index(docs, 'category_b'),
            'word_grid': word_grid,
            # * word_grid (list (tr) of lists (td) of lists [keyword (str), count (int)])
            'size': sizes
        }

        with open(self.FILENAME_EXPORT, 'w') as f:
        #with open('/home/tim/Uni/HPI/workspace/landscape_d3/data/finalnews.modir.json', 'w') as f:
            f.write(json.dumps(modir))

    @abstractmethod
    def _get_node_sent(self, node_id):
        # default return []
        raise NotImplementedError()

    @abstractmethod
    def _get_node_received(self, node_id):
        # default return []
        raise NotImplementedError()

    @abstractmethod
    def _get_node_email(self, node_id):
        # default return ''
        raise NotImplementedError()

    @abstractmethod
    def _get_node_org(self, node_id):
        # default return ''
        raise NotImplementedError()

    @abstractmethod
    def _produce_docs(self):
        raise NotImplementedError()

# {"idx":0,"id":"1692781","name":"Simon Stannus","freq":2,"doc_freq":2,"degree":2,"degree_weighted":4}
# {"idx":0,"id":"http:\/\/www.wikidata.org\/entity\/Q157617","name":"Commerzbank","type":"ORGANIZATION","freq":5133,"doc_freq":3565,"degree":2872,"degree_weighted":27435}
# node2docs
# node2nodes
