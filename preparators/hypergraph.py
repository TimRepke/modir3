from abc import ABC, abstractmethod
import numpy as np
from scipy.sparse import lil_matrix, spmatrix, csr_matrix, save_npz, load_npz
from .gensim_processor import GensimProcessor
from .hnswtree import HNSWTree
import ujson as json
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

    def assert_files(self):
        return os.path.isfile(self.FILENAME_DOC2DOCS) and \
               os.path.isfile(self.FILENAME_DOC2DOCS_NEG) and \
               os.path.isfile(self.FILENAME_NODE2DOCS) and \
               os.path.isfile(self.FILENAME_NODE2NODES) and \
               os.path.isfile(self.FILENAME_NODES) and \
               os.path.isfile(self.FILENAME_VECTORS)

    def prepare_graph(self):
        if self.assert_files():
            print('  - loading from files')
            self._load_from_files()
        else:
            print('  - building from scratch')
            self.vectors = np.memmap(self.FILENAME_VECTORS, dtype=np.float32, mode='w+',
                                     shape=(self.num_docs, self.input_dimensions))
            self.doc2docs = lil_matrix((self.num_docs, self.num_docs), dtype=np.float32)
            self.doc2docs_neg = lil_matrix((self.num_docs, self.num_docs), dtype=np.float32)
            self.nodes = {}

            self._prepare_graph_docs()
            self._prepare_graph()
            self._build_node_matrices()
            self._save_to_files()

        self._is_prepared = True

    def _prepare_graph_docs(self):
        for i, vector in enumerate(self.gensim_processor.vectors):
            self.vectors[i] = np.array(vector)
        print('  - loaded vectors into memmap')

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
        print('  - prepared doc2doc and doc2doc_neg')

    def _load_from_files(self):
        self.vectors = np.memmap(self.FILENAME_VECTORS, dtype=np.float32,
                                 shape=(self._num_docs, self.input_dimensions))
        self.doc2docs = load_npz(self.FILENAME_DOC2DOCS)
        self.doc2docs_neg = load_npz(self.FILENAME_DOC2DOCS_NEG)
        self.node2docs = load_npz(self.FILENAME_NODE2DOCS)
        self.node2nodes = load_npz(self.FILENAME_NODE2NODES)
        with open(self.FILENAME_NODES, 'r') as f:
            self.nodes = json.load(f)

    def _save_to_files(self):
        del self.vectors  # resetting here so that vectors are consistently read only for later use
        self.vectors = np.memmap(self.FILENAME_VECTORS, dtype=np.float32, shape=(self._num_docs, self.input_dimensions))

        with open(self.FILENAME_NODES, 'w') as f:
            json.dump(self.nodes, f)

        # lil (Row-based linked list sparse matrix) are more efficient for building matrix
        # csr (Compressed Sparse Row format) is more efficient for arithmetic ops
        self.doc2docs = self.doc2docs.tocsr()
        self.doc2docs_neg = self.doc2docs_neg.tocsr()
        save_npz(self.FILENAME_DOC2DOCS, self.doc2docs)
        save_npz(self.FILENAME_DOC2DOCS_NEG, self.doc2docs_neg)
        save_npz(self.FILENAME_NODE2DOCS, self.node2docs)
        save_npz(self.FILENAME_NODE2NODES, self.node2nodes)

    def _build_node_matrices(self):
        self.node2docs = lil_matrix((len(self.nodes), self._num_docs), dtype=np.int16)
        self.node2nodes = lil_matrix((len(self.nodes), len(self.nodes)), dtype=np.int16)
        for node in self.nodes.values():
            for doc_id in node['docs']:
                self.node2docs[node['idx'], doc_id] += 1
            del node['docs']

            for idx in node['nodes']:
                self.node2nodes[node['idx'], idx] += 1
            del node['nodes']

            node['freq'] = int(self.node2docs[node['idx']].sum())
            node['doc_freq'] = int(self.node2docs[node['idx']].getnnz())
            node['degree'] = int(self.node2nodes[node['idx']].getnnz())
            node['degree_weighted'] = int(self.node2nodes[node['idx']].sum())

        if self.min_node2doc_count is not None:
            self.node2docs[self.node2docs < self.min_node2doc_count] = .0
        if self.min_node2node_count is not None:
            self.node2nodes[self.node2nodes < self.min_node2node_count] = .0
        self.node2docs = self.node2docs.tocsc()
        self.node2nodes = self.node2nodes.tocsr()

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

    # for each doc -> neighbour docs
    # for each doc -> non-neighbour docs (optional)
    # for each doc -> target node (needed?)
    # for each node -> associated docs
