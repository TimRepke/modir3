from elasticsearch import Elasticsearch, helpers
import ujson as json
from collections import Counter
import logging

logging.getLogger('elasticsearch.trace').setLevel(0)
logging.getLogger('elasticsearch').setLevel(0)

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

    with open('../data/semantic_scholar_sample.json', 'w') as f:
        for i, author in authors:
            for doc in helpers.scan(es,
                                    index=index,
                                    query={
                                        "query": {'bool': {
                                            "must": [
                                                {"term": {"authors.ids": str(i)}}
                                            ]}
                                        },
                                        "size": 800
                                    }):
                f.write(json.dumps(doc['_source']) + '\n')
