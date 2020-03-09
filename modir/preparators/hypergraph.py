from scipy.sparse import spmatrix, coo_matrix, lil_matrix, csr_matrix, dok_matrix, save_npz, load_npz
from .gensim_processor import GensimProcessor
from collections import Counter
from abc import ABC, abstractmethod
from .hnswtree import HNSWTree
import json
import numpy as np
import timeit
import os


class HyperGraph(ABC):

    def __init__(self, gensim_processor: GensimProcessor, hnsw_tree: HNSWTree,
                 file_name, num_docs, input_dimensions, k_neighbourhood, k_global,
                 min_node_count=None, max_node_count=None,
                 min_node2doc_count=None, min_node2node_count=None):
        self.gensim_processor = gensim_processor
        self.hnsw_tree = hnsw_tree
        self.file_name = file_name
        self.k_neighbourhood = k_neighbourhood
        self.k_global = k_global
        self.min_node2doc_count = min_node2doc_count
        self.min_node2node_count = min_node2node_count

        self.min_node_count = min_node_count
        self.max_node_count = max_node_count

        self.input_dimensions = input_dimensions
        self._num_nodes = None
        self._num_docs = None

        # will be set to true once the data is initialised
        self._is_prepared = False

        self.vectors: np.memmap = None  # list of document vectors
        self.nodes: dict = None

        self.document_index: dict = None  # mapping from new index to old index after filtering documents
        self.doc2docs: spmatrix = None  # row is doc idx, col is distance to col_idx doc
        self.doc2docs_neg: spmatrix = None  # row is doc idx, col is distance to col_idx doc
        self.node2docs: spmatrix = None  # row is node idx, col is num occurrences in col_idx doc
        self.node2nodes: spmatrix = None  # row is node idx, col is num docs edge to col_idx node appear in

    @property
    def is_prepared(self):
        return self._is_prepared

    @property
    def num_docs(self):
        if self._num_docs is None:
            self._num_docs = self.node2docs.shape[1]
            # self._num_docs = self.vectors.shape[0]
        return self._num_docs

    @property
    def num_nodes(self):
        if self._num_nodes is None:
            self._num_nodes = self.node2nodes.shape[0]
        return self._num_nodes

    @property
    def FILENAME_NODES(self):
        return f'{self.file_name}.hypergraph_nodes'

    @property
    def FILENAME_VECTORS(self):
        return f'{self.file_name}.hypergraph_vectors'

    @property
    def FILENAME_DOC_INDEX(self):
        return f'{self.file_name}.hypergraph_doc_index'

    @property
    def FILENAME_DOC2DOCS(self):
        return f'{self.file_name}.hypergraph_doc2docs.npz'

    @property
    def FILENAME_DOC2DOCS_NEG(self):
        return f'{self.file_name}.hypergraph_doc2docs_neg.npz'

    @property
    def FILENAME_NODE2DOCS(self):
        return f'{self.file_name}.hypergraph_node2docs.npz'

    @property
    def FILENAME_NODE2NODES(self):
        return f'{self.file_name}.hypergraph_node2nodes.npz'

    @abstractmethod
    def _prepare_graph(self):
        raise NotImplementedError()

    def prepare_graph(self):
        self._ensure_doc_vectors()
        self._ensure_node_data()
        self._ensure_node_matrices()
        self._ensure_doc2docs()
        self._is_prepared = True

    def _ensure_doc_vectors(self):
        if os.path.isfile(self.FILENAME_VECTORS):
            self.vectors = np.memmap(self.FILENAME_VECTORS, dtype=np.float32,
                                     shape=(self.gensim_processor.get_count(), self.input_dimensions))
            print('  - loaded document vectors from file')
        else:
            num_total_docs = self.gensim_processor.get_count()
            self.vectors = np.memmap(self.FILENAME_VECTORS, dtype=np.float32, mode='w+',
                                     shape=(num_total_docs, self.input_dimensions))
            for i, vector in enumerate(self.gensim_processor.vectors):
                self.vectors[i] = np.array(vector)
            del self.vectors  # resetting here so that vectors are consistently read only for later use
            self.vectors = np.memmap(self.FILENAME_VECTORS, dtype=np.float32,
                                     shape=(num_total_docs, self.input_dimensions))
            print('  - loaded document vectors into memmap')

    def _ensure_doc2docs(self):
        if os.path.isfile(self.FILENAME_DOC2DOCS) and os.path.isfile(self.FILENAME_DOC2DOCS_NEG):
            self.doc2docs = load_npz(self.FILENAME_DOC2DOCS)
            self.doc2docs_neg = load_npz(self.FILENAME_DOC2DOCS_NEG)
            print('  - loaded doc2docs and doc2docs_neg from file')
        else:
            print('  - preparing doc2doc and doc2doc_neg...')
            self.doc2docs = lil_matrix((self.num_docs, self.num_docs), dtype=np.float32)
            self.doc2docs_neg = lil_matrix((self.num_docs, self.num_docs), dtype=np.float32)

            rev_index = {v: k for k, v in self.document_index.items()}
            for oi, (vector, doc) in enumerate(zip(self.vectors, self.gensim_processor.documents)):
                # skip documents that are no longer connected to any nodes
                if oi not in self.document_index:
                    continue
                ni = self.document_index[oi]

                # get some neighbourhood documents
                doc_ids, distances = self.hnsw_tree.get_n(vector, self.k_neighbourhood * 5)
                distances = [dist for odid, dist in zip(doc_ids[0], distances[0])
                             if odid in self.document_index and odid != oi][:self.k_neighbourhood]
                doc_ids = [self.document_index[odid] for odid in doc_ids[0]
                           if odid in self.document_index and odid != oi][:self.k_neighbourhood]

                self.doc2docs[ni, doc_ids] = distances

                # get some global, non-neighbourhood documents
                neg_indices = np.random.choice(a=self.num_docs, size=self.k_global, replace=False)
                neg_vectors = self.vectors[[rev_index[negi] for negi in neg_indices]]
                distances = ((vector - neg_vectors) ** 2).sum(axis=1)
                self.doc2docs_neg[ni, neg_indices[neg_indices != ni]] = distances[neg_indices != ni]

            self.doc2docs = self.doc2docs.tocsr()
            self.doc2docs_neg = self.doc2docs_neg.tocsr()
            save_npz(self.FILENAME_DOC2DOCS, self.doc2docs)
            save_npz(self.FILENAME_DOC2DOCS_NEG, self.doc2docs_neg)
            print('  - prepared doc2doc and doc2doc_neg')

    def _ensure_node_data(self):
        if os.path.isfile(self.FILENAME_NODES):
            with open(self.FILENAME_NODES, 'r') as f:
                self.nodes = json.load(f)
            print('  - loaded node data from file')
        else:
            print('  - preparing node data...')
            time0 = timeit.default_timer()
            self.nodes = {}
            self._prepare_graph()

            with open(self.FILENAME_NODES, 'w') as f:
                json.dump(self.nodes, f)
            print(f'  - prepared node data - {timeit.default_timer() - time0:.4f}s')

    def _ensure_node_matrices(self):
        if os.path.isfile(self.FILENAME_NODE2DOCS) and os.path.isfile(self.FILENAME_NODE2NODES):
            self.node2docs = load_npz(self.FILENAME_NODE2DOCS)
            self.node2nodes = load_npz(self.FILENAME_NODE2NODES)
            with open(self.FILENAME_DOC_INDEX, 'r') as f:
                self.document_index = json.load(f)
            print(f'  - loaded node matrices from files, '
                  f'node2docs: {self.node2docs.shape}, '
                  f'node2nodes: {self.node2nodes.shape}')
        else:
            print('  - preparing node matrices...')
            time0 = timeit.default_timer()
            # self.node2docs = coo_matrix((len(self.nodes), self.num_docs), dtype=np.int16)
            # self.node2nodes = coo_matrix((len(self.nodes), len(self.nodes)), dtype=np.int16)

            self._build_node_matrices()

            print(f'  - node2docs: {self.node2docs.shape}, '
                  f'node2nodes: {self.node2nodes.shape} - '
                  f'{timeit.default_timer() - time0:.4f}s')

            with open(self.FILENAME_DOC_INDEX, 'w') as f:
                json.dump(self.document_index, f)
            print('  - updated filtered document index')

            with open(self.FILENAME_NODES, 'w') as f:
                json.dump(self.nodes, f)
            print('  - updated node data')

            save_npz(self.FILENAME_NODE2DOCS, self.node2docs)
            save_npz(self.FILENAME_NODE2NODES, self.node2nodes)
            print(f'  - prepared node matrices from files, '
                  f'node2docs: {self.node2docs.shape}, '
                  f'node2nodes: {self.node2nodes.shape}')

    def _build_node_matrices(self):
        time0 = timeit.default_timer()

        # remove nodes that appear too little or too often
        nodes_filtered = {node['id']: node
                          for node in self.nodes.values()
                          if (self.max_node_count is None or self.max_node_count >= len(set(node['docs']))) and
                          (self.min_node_count is None or self.min_node_count <= len(set(node['docs'])))}
        for i, node in enumerate(nodes_filtered.values()):
            node['idx_orig'] = node['idx']
            node['idx'] = i
        nodes_index = {node['id']: i for i, node in enumerate(nodes_filtered.values())}
        print(f'  - nodes total: {len(self.nodes)}, nodes filtered: {len(nodes_filtered)}')

        # build a mapping of which nodes appear in which documents
        n2d = [(nodes_index[node['id']], di) for node in nodes_filtered.values() for di in node['docs']]
        n2d = Counter(n2d)
        n2d = [(nid, did, c) for (nid, did), c in n2d.items() if c >= self.min_node2doc_count]
        relevant_docs = set([did for _, did, _ in n2d])
        self.document_index = {odid: ndid for ndid, odid in enumerate(relevant_docs)}
        node2docs = coo_matrix(([c for _, _, c in n2d],
                                ([i for i, _, _ in n2d],
                                 [self.document_index[j] for _, j, _ in n2d])),
                               shape=(len(nodes_filtered), len(self.document_index)), dtype=np.int16)
        self.node2docs = node2docs.tocsr()
        print(f'  - non-zero node2docs: {self.node2docs.getnnz()} after {timeit.default_timer() - time0:.4f}s')

        # build actual node to node network
        n2n = [(nodes_index[node['id']], nodes_index[nid])
               for node in nodes_filtered.values()
               for nid in node['nodes']
               if nid in nodes_filtered]
        n2n = Counter(n2n)
        n2n = [(i, j, c) for (i, j), c in n2n.items() if c >= self.min_node2node_count]
        node2nodes = coo_matrix(([c for _, _, c in n2n],
                                 ([i for i, _, _ in n2n],
                                  [j for _, j, _ in n2n])),
                                shape=(len(nodes_filtered), len(nodes_filtered)), dtype=np.int16)
        self.node2nodes = node2nodes.tocsr()

        self.nodes = nodes_filtered
        print(f'  - non-zero node2nodes: {self.node2nodes.getnnz()} after {timeit.default_timer() - time0:.4f}s')

    def _assert_node(self, name, values=None):
        if name not in self.nodes:
            self.nodes[name] = {
                'idx': len(self.nodes),
                'docs': [],
                'nodes': []
            }
            if values is not None:
                for k, v in values.items():
                    self.nodes[name][k] = v

        return self.nodes[name]
