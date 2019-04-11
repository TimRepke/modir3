from scipy.sparse import spmatrix, coo_matrix, lil_matrix, csr_matrix, dok_matrix, save_npz, load_npz
from .gensim_processor import GensimProcessor
from collections import Counter
from abc import ABC, abstractmethod
from .hnswtree import HNSWTree
import ujson as json
import numpy as np
import timeit
import os


class HyperGraph(ABC):

    def __init__(self, gensim_processor: GensimProcessor, hnsw_tree: HNSWTree,
                 file_name, num_docs, input_dimensions, k_neighbourhood, k_global,
                 min_node2doc_count=None, min_node2node_count=None):
        self.gensim_processor = gensim_processor
        self.hnsw_tree = hnsw_tree
        self.file_name = file_name
        self.k_neighbourhood = k_neighbourhood
        self.k_global = k_global
        self.min_node2doc_count = min_node2doc_count
        self.min_node2node_count = min_node2node_count

        self._num_docs = num_docs
        self.input_dimensions = input_dimensions
        self._num_nodes = None

        # will be set to true once the data is initialised
        self._is_prepared = False

        self.vectors: np.memmap = None  # list of document vectors
        self.nodes: dict = None

        self.doc2docs: spmatrix = None  # row is doc idx, col is distance to col_idx doc
        self.doc2docs_neg: spmatrix = None  # row is doc idx, col is distance to col_idx doc
        self.node2docs: spmatrix = None  # row is node idx, col is num occurrences in col_idx doc
        self.node2nodes: spmatrix = None  # row is node idx, col is num docs edge to col_idx node appear in

    @property
    def is_prepared(self):
        return self._is_prepared

    @property
    def num_docs(self):
        if not self._num_docs:
            self._num_docs = self.vectors.shape[0]
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
        self._ensure_doc2docs()
        self._ensure_node_data()
        self._ensure_node_matrices()
        self._is_prepared = True

    def _ensure_doc_vectors(self):
        if os.path.isfile(self.FILENAME_VECTORS):
            self.vectors = np.memmap(self.FILENAME_VECTORS, dtype=np.float32,
                                     shape=(self._num_docs, self.input_dimensions))
            print('  - loaded document vectors from file')
        else:
            self.vectors = np.memmap(self.FILENAME_VECTORS, dtype=np.float32, mode='w+',
                                     shape=(self.num_docs, self.input_dimensions))
            for i, vector in enumerate(self.gensim_processor.vectors):
                self.vectors[i] = np.array(vector)
            del self.vectors  # resetting here so that vectors are consistently read only for later use
            self.vectors = np.memmap(self.FILENAME_VECTORS, dtype=np.float32,
                                     shape=(self._num_docs, self.input_dimensions))
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

            for i, (vector, doc) in enumerate(zip(self.vectors, self.gensim_processor.documents)):
                # get some neighbourhood documents
                doc_ids, distances = self.hnsw_tree.get_n(vector, self.k_neighbourhood + 1)
                doc_ids = doc_ids[0]
                distances = distances[0]
                self.doc2docs[i, doc_ids[doc_ids != i]] = distances[doc_ids != i]

                # get some global, non-neighbourhood documents
                neg_indices = np.random.choice(a=self.num_docs, size=self.k_global, replace=False)
                neg_vectors = self.vectors[neg_indices]
                distances = ((vector - neg_vectors) ** 2).sum(axis=1)
                self.doc2docs_neg[i, neg_indices[neg_indices != i]] = distances[neg_indices != i]

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
            print('  - loaded node matrices from files')
        else:
            print('  - preparing node matrices...')
            time0 = timeit.default_timer()
            self.node2docs = coo_matrix((len(self.nodes), self.num_docs), dtype=np.int16)
            self.node2nodes = coo_matrix((len(self.nodes), len(self.nodes)), dtype=np.int16)
            print(f'  - node2docs: {self.node2docs.shape}, '
                  f'node2nodes: {self.node2nodes.shape} - '
                  f'{timeit.default_timer() - time0:.4f}s')

            self._build_node_matrices()

            with open(self.FILENAME_NODES, 'w') as f:
                json.dump(self.nodes, f)
            print('  - updated node data')

            save_npz(self.FILENAME_NODE2DOCS, self.node2docs)
            save_npz(self.FILENAME_NODE2NODES, self.node2nodes)
            print('  - prepared node matrices')

    def _build_node_matrices(self):
        time0 = timeit.default_timer()
        n2d = [(node['idx'], di) for node in self.nodes.values() for di in node['docs']]
        n2d = Counter(n2d)
        if self.min_node2doc_count is None:
            n2d = [(i, j, c) for (i, j), c in n2d.items()]
        else:
            n2d = [(i, j, c) for (i, j), c in n2d.items() if c >= self.min_node2doc_count]
        self.node2docs = coo_matrix(([c for _, _, c in n2d],
                                     ([i for i, _, _ in n2d],
                                      [j for _, j, _ in n2d])),
                                    shape=(len(self.nodes), self.num_docs), dtype=np.int16)
        self.node2docs = self.node2docs.tocsr()
        print(f'  - non-zero node2docs: {self.node2docs.getnnz()} after {timeit.default_timer() - time0:.4f}s')

        n2n = [(node['idx'], di) for node in self.nodes.values() for di in node['docs']]
        n2n = Counter(n2n)
        if self.min_node2node_count is None:
            n2n = [(i, j, c) for (i, j), c in n2n.items()]
        else:
            n2n = [(i, j, c) for (i, j), c in n2n.items() if c >= self.min_node2node_count]
        self.node2nodes = coo_matrix(([c for _, _, c in n2n],
                                      ([i for i, _, _ in n2n],
                                       [j for _, j, _ in n2n])),
                                     shape=(len(self.nodes), self.num_docs), dtype=np.int16)
        self.node2nodes = self.node2nodes.tocsr()
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
