* `ambiverse.py` is a script that applies the ambiverse entity extraction and linking to wikidata on the news dataset
* `dictionary.py` is a script for exploration if you want to check out the word distribution
* `extract_curated_network.py` contains the query used to produce the "large" sample from the semantic scholar datset
* `gensim_doc2vec.py` a script for early experiments, produces an output that can be plugged into the tensorprojector
* `get_toy_subset.py` get the "small" dataset from semantic scholar
* `mcc2modir.py` generated a fake MODiR visualisation that only places points based on document embeddings and nodes are the average of related document embeddings
* `network.py` produces `network.html` (or at least the json dump that can be pasted there). this was used to figure out how to filter densely connected input networks as is the case in the commerzbank news example.
* `news2modir.py` similar to `mcc2modir.py`
* `semantic_scholar2solr.py` assuming you downloaded the full semantic scholar dump (was easily accessible in 2018, now they don't provide the simple download anymore), you can load it into elasticsearch with this script
