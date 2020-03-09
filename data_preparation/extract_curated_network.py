from elasticsearch import Elasticsearch, helpers
import ujson as json
from collections import Counter
import logging

logging.getLogger('elasticsearch.trace').setLevel(0)
logging.getLogger('elasticsearch').setLevel(0)

co_authors = {
    "aggs": {
        "2": {
            "terms": {
                "field": "authors.name",
                "size": 150,
                "order": {
                    "_count": "desc"
                }
            }
        }
    },
    "size": 0,
    "_source": {
        "excludes": []
    },
    "stored_fields": [
        "*"
    ],
    "script_fields": {},
    "docvalue_fields": [
        "year"
    ],
    "query": {
        "bool": {
            "must": [
                {
                    "match_all": {}
                },
                {
                    "match_phrase": {
                        "authors.ids": {
                            "query": 1777528
                        }
                    }
                }
            ],
            "filter": [],
            "should": [],
            "must_not": []
        }
    }
}

if __name__ == '__main__':
    es = Elasticsearch(
        hosts=[{'host': '172.16.64.23', 'port': 9200}],  # isfet (kibana: 5601)
        use_ssl=False,
        verify_certs=False
    )
    index = 'ss'

    authors = [(1947334, "Wai-Tat Fu"),
               (1738271, "Shimei Pan"),
               (1728478, "Donald A.Norman"),
               (1695715, "Michael Stonebraker"),
               (1704011, "Divesh Srivastava"),
               (1812612, "Christopher D.Manning"),
               (1751762, "Yoshua Bengio"),
               (1701538, "Andrew Y.Ng"),
               (34740554, "Ian J.Goodfellow"),
               (2166511, "Richard Socher"),
               (1760871, "Aaron C.Courville"),
               (1777528, "Hugo Larochelle"),
               (2354728, "Andrej Karpathy"),
               (3216322, "Li Fei - Fei"),
               (35609041, "Michael S.Bernstein"),
               (2285165, "Jonathan Krause"),
               (1695689, "Geoffrey Hinton")]

    for ia in range(len(authors)):
        id_a, author_a = authors[ia]
        for ib in range(ia + 1, len(authors)):
            id_b, author_b = authors[ib]
            res = es.search(index=index,
                            body={
                                "query": {
                                    "bool": {
                                        "must": [
                                            {"term": {"authors.ids": str(id_a)}},
                                            {"term": {"authors.ids": str(id_b)}}
                                        ],
                                        "must_not": [],
                                        "should": []
                                    }
                                },
                                "from": 0, "size": 500, "sort": [], "aggs": {}
                            })
            if res['hits']['total'] == 0:
                continue

            print('> {} <-> {} | {} papers\n'
                  '  - _id: {}\n'
                  '  - venue: {}\n'
                  '  - journal: {}'.format(author_a,
                                           author_b,
                                           res['hits']['total'],
                                           [h['_id'] for h in res['hits']['hits']],
                                           dict(Counter([h['_source']['venue'] for h in res['hits']['hits']])),
                                           dict(Counter([h['_source']['journalName'] for h in res['hits']['hits']]))))
