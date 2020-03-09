import hnswlib
import numpy as np


class HNSWTree:
    def __init__(self, input_dims, input_size, space='l2', batch_size=200):
        """
        https://github.com/nmslib/hnswlib/blob/master/ALGO_PARAMS.md
        http://ann-benchmarks.com/index.html#algorithms
        https://rare-technologies.com/performance-shootout-of-nearest-neighbours-querying/

        Parameters
        ----------
        input_size
           Number of elements to be stored in the tree
        input_dims
           Dimensionality of the input vectors
        space
           possible options are l2, cosine or ip
        """
        self.space = space
        self.input_dims = input_dims
        self.input_size = input_size
        self.batch_size = batch_size
        self.tree = None

    def init_file(self, file_name):
        """ Init a previously built tree from file

        Parameters
        ----------
        file_name

        """
        self.tree = hnswlib.Index(space=self.space, dim=self.input_dims)
        self.tree.load_index(file_name, max_elements=self.input_size)

    def init_params(self, ef, M, ef_construction, n_threads):
        """ Init a new tree with parameters

        Parameters
        ----------
        ef
           The size of the dynamic list for the nearest neighbors (used during the search).
           Higher ef leads to more accurate but slower search. ef cannot be set lower than the
           number of queried nearest neighbors k. The value ef of can be anything between k
           and the size of the dataset.
        M
           is tightly connected with internal dimensionality of the data. Strongly affects the memory consumption (~M)
           Higher M leads to higher accuracy/run_time at fixed ef/efConstruction
        ef_construction
           controls index search speed/build speed trade-off
        n_threads
           Number of threads for parallel processing
        """
        self.tree = hnswlib.Index(space=self.space, dim=self.input_dims)
        self.tree.init_index(max_elements=self.input_size, ef_construction=ef_construction, M=M)
        self.tree.set_ef(ef)
        self.tree.set_num_threads(n_threads)

    def fill(self, vectors, is_batched=True):
        if is_batched:
            for batch in vectors:
                self.tree.add_items(np.array(batch))
        else:
            self.tree.add_items(np.array(vectors))

    def get_n_from_batches(self, x, k):
        for batch in x:
            yield self.tree.knn_query(batch, k=k)

    def get_n_batched(self, x, k, batch_size):
        for batch in range(len(x) // batch_size + 1):
            yield self.tree.knn_query(x[batch * batch_size:(batch + 1) * batch_size], k=k)

    def get_n(self, x, k):
        return self.tree.knn_query(x, k=k)

    def save(self, file_name):
        self.tree.save_index(file_name)
