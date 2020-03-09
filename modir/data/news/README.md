# News Datasets

describe (reuters+bloomberg, filtered for commerzbank)

### gensim
```
cd scripts/
python gensim_doc2vec.py --raw-data=../data/news/coba_news.json --processor=news --processor-target=../data/news/news_docs.txt

python gensim_doc2vec.py --d2v-mode=train --model=../data/news/d2vmodel.pickle --documents=../data/news/news_docs.txt --d2v-min-count=10 --d2v-max-vocab=20000 --d2v-size=48 --d2v-epochs=100 --d2v-workers=4

python gensim_doc2vec.py --d2v-mode=apply --model=../data/news/d2vmodel.pickle --documents-in=../data/news/coba_news.json --documents-out=../data/news/coba_news_d2v.json 
```