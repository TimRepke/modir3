import numpy as np
import timeit
import torch
import torch.nn.functional as F
from torch import optim
from torch import nn
from collections import deque
from typing import Union, Optional
from tqdm import tqdm
import matplotlib.pyplot as plt
from .export import make_svg


class Model(nn.Module):
    def __init__(self, num_docs, nan_safety=True, w1=1., w2=1., w3=1.):
        super().__init__()
        self.nan_safety = nan_safety
        self.use_cuda = False
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3

        # nn.Parameter
        # A simple lookup table that stores embeddings of a fixed dictionary and size.
        self.positions = nn.Embedding(num_embeddings=num_docs, embedding_dim=2)
        self.loss1 = nn.MSELoss(reduction='sum')
        self.loss2 = nn.MSELoss(reduction='sum')

        init_range = 1.0
        self.positions.weight.data.uniform_(-init_range, init_range)
        # self.positions.weight.data.uniform_(-0, 0)

    def contains_nan(self):
        if not self.nan_safety:
            return False
        embedding = self.get_embedding()
        return np.isnan(embedding.sum())

    def get_embedding(self):
        if self.use_cuda:
            return self.positions.weight.cpu().data.numpy()
        return self.positions.weight.data.numpy()

    def save_embedding(self, file_name):
        embedding = self.get_embedding()
        with open(file_name, 'w') as f:
            for r in embedding:
                e = ','.join([f'{ei:.8f}' for ei in r])
                f.write(f'{e}\n')

    def forward(self, doc_i, neighbours, neighbour_distances, global_docs, global_distances, related_docs):
        doc_pos = self.positions(torch.LongTensor([doc_i]))
        neighbour_pos = self.positions(torch.LongTensor(neighbours))
        globals_pos = self.positions(torch.LongTensor(global_docs))
        related_pos = self.positions(torch.LongTensor(related_docs))

        distances = ((doc_pos - neighbour_pos) ** 2).sum(dim=1)  # .sqrt()
        target_distances = torch.FloatTensor(neighbour_distances)
        loss = self.loss1(distances, target_distances)

        distances_global = ((doc_pos - globals_pos) ** 2).sum(dim=1)  # .sqrt()
        target_distances_global = torch.FloatTensor(global_distances)
        loss_global = self.loss2(distances_global, target_distances_global)

        related_center = related_pos.sum(dim=0) / related_pos.size(0)
        distances_related = ((related_center - related_pos) ** 2).sum(dim=1).sqrt()

        # print(doc_i, loss.item(), neighbours, distances.data, neighbour_distances)
        return self.w1 * loss + self.w2 * loss_global + self.w3 * distances_related.sum()


class Trainer:
    def __init__(self, hypergraph, learning_rate=0.01, related_samples=10):
        self.hypergraph = hypergraph
        self.model = Model(num_docs=self.hypergraph.num_docs, )
        self.optimizer = optim.SGD(self.model.parameters(), lr=learning_rate)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=20, gamma=0.5, last_epoch=-1)
        self.related_samples = related_samples

    def train(self, intermediate_files=None):

        time0 = timeit.default_timer()
        time1 = timeit.default_timer()
        cnt = 0
        loss = 0.0

        normed_doc2docs_global = self.hypergraph.doc2docs_neg
        normed_doc2docs = self.hypergraph.doc2docs
        maxi = normed_doc2docs.max()
        maxi_global = 1. / normed_doc2docs_global.max(axis=1).data
        normed_doc2docs = normed_doc2docs.multiply(maxi_global).tocsr()
        normed_doc2docs_global = normed_doc2docs_global.multiply(maxi_global).tocsr()

        # print(f'maxi: {maxi}, maxi_global: {maxi_global}')
        # print(f'mean: {np.mean(self.hypergraph.doc2docs.data)}, '
        #       f'median: {np.median(self.hypergraph.doc2docs.data)}')
        # print(f'mean_neg: {np.mean(self.hypergraph.doc2docs_neg.data)}, '
        #       f'median_neg: {np.median(self.hypergraph.doc2docs_neg.data)}')
        #
        # print(f'normed mean: {np.mean(normed_doc2docs.data)}, '
        #       f'normed median: {np.median(normed_doc2docs.data)}')
        # print(f'normed mean global: {np.mean(normed_doc2docs_global.data)},'
        #       f'normed median global: {np.median(normed_doc2docs_global.data)}')
        # plt.hist(normed_doc2docs.data, bins=100)
        # plt.hist(normed_doc2docs_global.data, bins=100, alpha=0.7)
        # plt.show()

        try:
            categories = [doc[self.hypergraph.gensim_processor.COMMUNITY_KEY]
                          for doc in self.hypergraph.gensim_processor.documents]
        except KeyError:
            categories = None

        for epoch_i in range(200):
            print(f'Beginning epoch {epoch_i} with lr: {self.optimizer.param_groups[0]["lr"]}, '
                  f'momentum: {self.optimizer.param_groups[0]["momentum"]}, '
                  f'dampening: {self.optimizer.param_groups[0]["dampening"]}...')

            if intermediate_files is not None and (epoch_i % 5) == 0:
                make_svg(f'{intermediate_files}_{epoch_i}.svg', embedding=self.model.get_embedding(), labels=categories)

            time1 = timeit.default_timer()

            for doc_i, doc_row in enumerate(normed_doc2docs):
                doc_global = normed_doc2docs_global[doc_i]
                # get all nodes connected to this document
                doc_nodes = self.hypergraph.node2docs.T.tocsr()[doc_i].indices
                # get all documents of these nodes are also connected to
                nodes_docs = self.hypergraph.node2docs.tocsr()[doc_nodes].indices
                if len(nodes_docs) >= self.related_samples:
                    nodes_docs = np.random.choice(nodes_docs, self.related_samples, replace=False)

                self.optimizer.zero_grad()
                loss = self.model.forward(doc_i,
                                          doc_row.indices,  # indices of documents in neighbourhood of doc_i
                                          doc_row.data,  # distances of documents in neighbourhood of doc_i
                                          doc_global.indices,
                                          doc_global.data,
                                          nodes_docs)
                loss.backward()
                self.optimizer.step()
                cnt += 1
            self.scheduler.step()
            print(f'> Done with epoch {epoch_i}, loss: {loss.item()}... '
                  f'Time total elapsed: {timeit.default_timer() - time0:.1f}s, '
                  f'Time for epoch: {timeit.default_timer() - time1:.2f}s '
                  f'({(timeit.default_timer() - time1) / 60:.1f}min)')
            if self.model.contains_nan():
                raise ValueError(f'NaN error! loss:{loss}, epoch: {epoch_i}')
