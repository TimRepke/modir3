# AMiner Data Description
*(copied from http://aminer.org/billboard/aminernetwork)*

## Overview
This dataset is designed for research purpose only.

The content of this data includes paper information, paper citation, author information and author collaboration. 2,092,356 papers and 8,024,869 citations between them are saved in the file AMiner-Paper.rar; 1,712,433 authors are saved in the file AMiner-Author.zip and 4,258,615 collaboration relationships are saved in the file AMiner-Coauthor.zip.

## Files
 
#### AMiner-Paper.rar [download](http://arnetminer.org/lab-datasets/aminerdataset/AMiner-Paper.rar)
This file saves the paper information and the citation network. The format is as follows:
```
#index ---- index id of this paper
#* ---- paper title
#@ ---- authors (separated by semicolons)
#o ---- affiliations (separated by semicolons, and each affiliaiton corresponds to an author in order)
#t ---- year
#c ---- publication venue
#% ---- the id of references of this paper (there are multiple lines, with each indicating a reference)
#! ---- abstract
```
The following is an example:
```
#index 1083734
#* ArnetMiner: extraction and mining of academic social networks
#@ Jie Tang;Jing Zhang;Limin Yao;Juanzi Li;Li Zhang;Zhong Su
#o Tsinghua University, Beijing, China;Tsinghua University, Beijing, China;Tsinghua University, Beijing, China;Tsinghua University, Beijing, China;IBM, Beijing, China;IBM, Beijing, China
#t 2008
#c Proceedings of the 14th ACM SIGKDD international conference on Knowledge discovery and data mining
#% 197394
#% 220708
#% 280819
#% 387427
#% 464434
#% 643007
#% 722904
#% 760866
#% 766409
#% 769881
#% 769906
#% 788094
#% 805885
#% 809459
#% 817555
#% 874510
#% 879570
#% 879587
#% 939393
#% 956501
#% 989621
#% 1117023
#% 1250184
#! This paper addresses several key issues in the ArnetMiner system, which aims at extracting and mining academic social networks. Specifically, the system focuses on: 1) Extracting researcher profiles automatically from the Web; 2) Integrating the publication data into the network from existing digital libraries; 3) Modeling the entire academic network; and 4) Providing search services for the academic network. So far, 448,470 researcher profiles have been extracted using a unified tagging approach. We integrate publications from online Web databases and propose a probabilistic framework to deal with the name ambiguity problem. Furthermore, we propose a unified modeling approach to simultaneously model topical aspects of papers, authors, and publication venues. Search services such as expertise search and people association search have been provided based on the modeling results. In this paper, we describe the architecture and main features of the system. We also present the empirical evaluation of the proposed methods.
```

#### AMiner-Author.zip [download](http://arnetminer.org/lab-datasets/aminerdataset/AMiner-Author.zip)
This file saves the author information. The format is as follows:
```
#index ---- index id of this author
#n ---- name  (separated by semicolons)
#a ---- affiliations  (separated by semicolons)
#pc ---- the count of published papers of this author
#cn ---- the total number of citations of this author
#hi ---- the H-index of this author
#pi ---- the P-index with equal A-index of this author
#upi ---- the P-index with unequal A-index of this author
#t ---- research interests of this author  (separated by semicolons)
```
Note: Please refer to [J. Stallings et al, Determining scientific impact using a collaboration index](http://www.pnas.org/content/110/24/9680) for the concepts of P-index and A-index.
 
The following is an example:
```
#index 1488277
#n Juanzi Li
#a Tsinghua University;Department of Computer Science & Technology, Tsinghua, University, Beijing, China 100084
#pc 70
#cn 370
#hi 9
#pi 76.3254
#upi 73.7573
#t semantic web;social network;Semantic Annotation;ontology caching;semantic information;knowledge base
```

#### AMiner-Coauthor.zip [download](http://arnetminer.org/lab-datasets/aminerdataset/AMiner-Coauthor.zip)
This file saves the collaboration network among the authors in the second file. The format is as follows:
```
#00 11 22 ---- 00 means the index id of one author, 11 means the index id of another author, 22 means the number of collaborations btween them
```
The following is an example:
```
#693708 1658058 2
```