# MODiR 3.0 Reference Implementation

Please look at the READMEs in the different data folders for more information. Some skripts exist in data_preparation to enrich or filter the data beforehand.

This folder contains the main executable, there are lots of parameters. Check them out with `python modir3.py --help`. Here is an example execution:

```
python modir3.py --data-in=data/news/coba_news_amb.json --hnsw-file=data/news/tree --hnsw-ef=50 --hnsw-ef-init=30 --hnsw-M=16 --hnsw-threads=2 --d2v-max-vocab=20000 --d2v-min-count=10 --d2v-size=64 --d2v-epochs=100 --d2v-workers=6 --d2v-skip-empty --hypergraph-files=data/news/hypergraph --neighbourhood-k=5 --related-k=5 --global-k=5 --data-set=news --data-out=data/news/final --graph-min-node-count=30 --graph-max-node-count=700 --graph-min-node2doc-count=2 --graph-min-node2node-count=50
```

The main skript (`modir3.py`) constructs a processing pipeline of "processors". Each one takes data from a "spring" and writes its result to one or more "sink"s. This way, on re-runs, you don't have to execute everything again if not needed. Simply delete the files that should be updated.

To run it on your own dataset, check out `preparators/specifics/`. This includes implementations of abstract classes that you can use as a template for your dataset. Alternatively, you can process your data to follow one of the existing formats. We include a small selection of sample data so it's easier to interpret.

If you have questions or problems, please contact us or open an issue.
