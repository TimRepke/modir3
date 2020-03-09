# Joint Visualisation of Network and Text Data

Many large text collections exhibit graph structures, either inherent to the content itself or encoded in the metadata of the individual documents. Example graphs extracted from document collections are co-author networks, citation networks, or named-entity-cooccurrence networks. Furthermore, social networks can be extracted from email corpora, tweets, or social media. When it comes to visualising these large corpora, either the textual content or the network graph are used.

With MODiR (multi-objective dimensionality reduction), we propose to incorporate both, text and graph, to not only visualise the semantic information encoded in the documents' content but also the relationships expressed by the inherent network structure. To this end, we introduced a novel algorithm based on multi-objective optimisation to jointly position embedded documents and graph nodes in a two-dimensional landscape.

This repository contains the reference implementation for our JCDL 2020 paper "Visualising Large Document Collections by Jointly Modeling Text and Network Structure".

For more information on that project, please visit https://hpi.de/naumann/s/modir.html

```
@inproceedings{repke2020visualising,
  author = {Repke, Tim and Krestel, Ralf},
  booktitle = {Proceedings of the Joint Conference on Digital Libraries ({JCDL})},
  title = {Visualising Large Document Collections by Jointly Modeling Text and Network Structure},
  year = {2020},
  publisher {ACM},
  pages={1--11}
}

```

## Repository Structure
Each directory contains an additional README for more info.

* `data_preparation` contains skripts that might be helpful for enriching or filtering the data
* `frontend` contains a (deprecated) demo, please refer to https://github.com/TimRepke/modir-viewer for a more recent version
* `history` contains screenshots and early single-html-page demos of prototypes
* `modir` contains a processing pipeline for reading raw data, preparing and processing it, and generating an output that can be used by the viewer


