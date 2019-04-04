import argparse
import timeit
import time
import os
from preparators import *
from preparators.modir import Trainer

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hnsw-file', type=str,
                        help='File for the HNSW tree')
    parser.add_argument('--hnsw-ef', type=int, default=50,
                        help='HNSW recall control\n -> higher ef leads to better accuracy, but slower search')
    parser.add_argument('--hnsw-ef-init', type=int, default=200,
                        help='HNSW speed tradeoff\n'
                             ' -> ef_construction - controls index search speed/build speed tradeoff')
    parser.add_argument('--hnsw-M', type=int, default=16,
                        help='HNSW memory factor; Strongly affects the memory consumption (~M)\n'
                             ' -> Higher M leads to higher accuracy/run_time at fixed ef/ef_construction')
    parser.add_argument('--hnsw-threads', type=int, default=4,
                        help='Number of threads for HNSW KNN tree to use')

    parser.add_argument('--d2v-max-vocab', type=int, default=10000,
                        help='max size of doc2vec vocab')
    parser.add_argument('--d2v-min-count', type=int, default=2,
                        help='min number of occurrences of a word')
    parser.add_argument('--d2v-size', type=int, default=128,
                        help='size of document vectors')
    parser.add_argument('--d2v-epochs', type=int, default=100,
                        help='number of epochs to train')
    parser.add_argument('--d2v-workers', type=int, default=8,
                        help='number of gensim workers')
    parser.add_argument('--d2v-allow-infer', action='store_true',
                        help='allow to infer vector if lookup is not possible during doc2vec apply')
    parser.add_argument('--d2v-skip-empty', action='store_true',
                        help='set flag to skip docs with empty text field')
    parser.add_argument('--gensim-logging', action='store_true',
                        help='turn on gensim logging. to pipe into file, use 2> ')

    parser.add_argument('--hypergraph-files', type=str,
                        help='Base for intermediate filenames for the hypergraph')
    parser.add_argument('--neighbourhood-k', type=int,
                        help='Size of k-neighbourhood')
    parser.add_argument('--global-k', type=int,
                        help='Size of non-k-neighbourhood')
    parser.add_argument('--related-k', type=int,
                        help='Size of related document neighbourhood (connected via node)')

    parser.add_argument('--data-set', type=str, choices=['aminer', 's2', 'enron', 'news', 'mcc'],
                        help='Which dataset is used')
    parser.add_argument('--data-enron-only-original', action='store_true',
                        help='If using --data-set=enron, add this flag to only consider non-duplicate emails')
    parser.add_argument('--data-papers-filter-venues', action='store_true',
                        help='Using a paper dataset, set flag to only include articles published in known communities')
    parser.add_argument('--data-in', type=str,
                        help='raw dataset input file')
    parser.add_argument('--data-out', type=str,
                        help='linear json-style dataset output file')
    cli_args = parser.parse_args()

    DIMS = cli_args.d2v_size

    print('Started at', time.strftime("%Y-%m-%d %H:%M"))

    # ---------------------------------------------------
    # Prepare and embed documents
    # ---------------------------------------------------
    print('----------------\n Starting Gensim Preparation')
    time0 = timeit.default_timer()
    gensim_processor = None
    if cli_args.data_set == 'aminer':
        gensim_processor = AminerGensimProcessor(filter_venue=cli_args.data_papers_filter_venues,
                                                 in_file=cli_args.data_in, out_file=cli_args.data_out,
                                                 skip_empty=cli_args.d2v_skip_empty)
    elif cli_args.data_set == 's2':
        gensim_processor = S2GensimProcessor(filter_venue=cli_args.data_papers_filter_venues,
                                             in_file=cli_args.data_in, out_file=cli_args.data_out,
                                             skip_empty=cli_args.d2v_skip_empty)
    elif cli_args.data_set == 'enron':
        gensim_processor = EnronGensimProcessor(only_original=cli_args.data_enron_only_original,
                                                in_file=cli_args.data_in, out_file=cli_args.data_out,
                                                skip_empty=cli_args.d2v_skip_empty)
    elif cli_args.data_set == 'news':
        gensim_processor = NewsGensimProcessor(in_file=cli_args.data_in, out_file=cli_args.data_out,
                                               skip_empty=cli_args.d2v_skip_empty)
    elif cli_args.data_set == 'mcc':
        gensim_processor = MCCGensimProcessor(in_file=cli_args.data_in, out_file=cli_args.data_out,
                                              skip_empty=cli_args.d2v_skip_empty)
    else:
        raise AttributeError(f'There is no processing for {cli_args.data_set}!')
    print(f'  - initialised processor for {cli_args.data_set}')

    if not gensim_processor.is_prepared():
        print('  > Data is not prepared, doing that now...')
        time1 = timeit.default_timer()
        gensim_processor.prepare()
        print(f'  - Prepared input data in: {timeit.default_timer() - time1:.4f}s')

    if not gensim_processor.is_trained():
        print('  > Model is not trained, doing that now...')
        time1 = timeit.default_timer()
        gensim_processor.train(min_count=cli_args.d2v_min_count, max_vocab_size=cli_args.d2v_max_vocab,
                               vector_size=cli_args.d2v_size, epochs=cli_args.d2v_epochs, workers=cli_args.d2v_workers,
                               verbosity=cli_args.gensim_logging)
        print(f'  - Trained model in: {timeit.default_timer() - time1:.4f}s')

    if not gensim_processor.is_applied():
        print('  > Model is not applied, doing that now...')
        time1 = timeit.default_timer()
        gensim_processor.apply(allow_infer=cli_args.d2v_allow_infer)
        print(f'  - Applied model in: {timeit.default_timer() - time1:.4f}s')

    print(f'  - Done with Gensim Processing, took: {timeit.default_timer() - time0:.4f}s')

    # ---------------------------------------------------
    # Build HNSW Tree
    # ---------------------------------------------------
    print('----------------\n Builing HNSW Tree')
    time0 = timeit.default_timer()
    tree = HNSWTree(input_dims=gensim_processor.get_dimensionality(), input_size=gensim_processor.get_count())
    if os.path.isfile(cli_args.hnsw_file):
        print(f'  - loading tree from {cli_args.hnsw_file}')
        tree.init_file(cli_args.hnsw_file)
    else:
        print('  - initialising fresh tree')
        tree.init_params(ef=cli_args.hnsw_ef, M=cli_args.hnsw_M, ef_construction=cli_args.hnsw_ef_init,
                         n_threads=cli_args.hnsw_threads)
        print(f'  - init done after: {timeit.default_timer() - time0:.4f}s\n    now filling...')
        tree.fill(gensim_processor.get_vectors_batched(batch_size=500), is_batched=True)
        print(f'  - filled tree after: {timeit.default_timer() - time0:.4f}s\n    now saving...')
        tree.save(cli_args.hnsw_file)
        print(f'  - saved tree to {cli_args.hnsw_file} after: {timeit.default_timer() - time0:.4f}s')
    print(f'  - Done building HNSW Tree, took: {timeit.default_timer() - time0:.4f}s')

    # ---------------------------------------------------
    # Prepare Hypergraph
    # ---------------------------------------------------
    print('----------------\n Starting HyperGraph Preparation')
    time0 = timeit.default_timer()
    hypergraph = None
    if cli_args.data_set == 'aminer':
        raise AttributeError(f'There is no processing for {cli_args.data_set}!')
    elif cli_args.data_set == 's2':
        hypergraph = S2HyperGraph(gensim_processor=gensim_processor, hnsw_tree=tree,
                                  file_name=cli_args.hypergraph_files,
                                  num_docs=gensim_processor.get_count(),
                                  input_dimensions=gensim_processor.get_dimensionality(),
                                  k_neighbourhood=cli_args.neighbourhood_k,
                                  k_global=cli_args.global_k,
                                  min_node2doc_count=None, min_node2node_count=2)
    elif cli_args.data_set == 'enron':
        raise AttributeError(f'There is no processing for {cli_args.data_set}!')
    elif cli_args.data_set == 'news':
        hypergraph = NewsHyperGraph(gensim_processor=gensim_processor, hnsw_tree=tree,
                                    file_name=cli_args.hypergraph_files,
                                    num_docs=gensim_processor.get_count(),
                                    input_dimensions=gensim_processor.get_dimensionality(),
                                    k_neighbourhood=cli_args.neighbourhood_k,
                                    k_global=cli_args.global_k,
                                    min_node2doc_count=3, min_node2node_count=10)
    elif cli_args.data_set == 'mcc':
        raise AttributeError(f'There is no processing for {cli_args.data_set}!')
    else:
        raise AttributeError(f'There is no processing for {cli_args.data_set}!')
    hypergraph.prepare_graph()
    print(f'  - init done after: {timeit.default_timer() - time0:.4f}s')
    print(f'  - initialised HyperGraph for {cli_args.data_set}')

    # ---------------------------------------------------
    # Train Layout
    # ---------------------------------------------------
    print('----------------\n Starting Layout Process')
    time0 = timeit.default_timer()
    t = Trainer(hypergraph=hypergraph, learning_rate=0.01, related_samples=cli_args.related_k)
    t.train(intermediate_files=cli_args.data_out)
    t.model.save_embedding(cli_args.data_out + '.pos')

    print(f'  - training done after: {timeit.default_timer() - time0:.4f}s')
    print(f'  - done training {cli_args.data_set}')

    print('Done at', time.strftime("%Y-%m-%d %H:%M"))
