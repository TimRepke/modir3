from elasticsearch import Elasticsearch, helpers
import ujson as json
import logging

files = ['s2-corpus-00',
         's2-corpus-01',
         's2-corpus-02',
         's2-corpus-03',
         's2-corpus-04',
         's2-corpus-05',
         's2-corpus-06',
         's2-corpus-07',
         's2-corpus-08',
         's2-corpus-09',
         's2-corpus-10',
         's2-corpus-11',
         's2-corpus-12',
         's2-corpus-13',
         's2-corpus-14',
         's2-corpus-15',
         's2-corpus-16',
         's2-corpus-17',
         's2-corpus-18',
         's2-corpus-19',
         's2-corpus-20',
         's2-corpus-21',
         's2-corpus-22',
         's2-corpus-23',
         's2-corpus-24',
         's2-corpus-25',
         's2-corpus-26',
         's2-corpus-27',
         's2-corpus-28',
         's2-corpus-29',
         's2-corpus-30',
         's2-corpus-31',
         's2-corpus-32',
         's2-corpus-33',
         's2-corpus-34',
         's2-corpus-35',
         's2-corpus-36',
         's2-corpus-37',
         's2-corpus-38',
         's2-corpus-39']
files = ['../data/sample-S2-records']

logging.getLogger('elasticsearch.trace').setLevel(0)
logging.getLogger('elasticsearch').setLevel(0)


def make_index(es: Elasticsearch, es_index: str):
    es.indices.delete(es_index, allow_no_indices=True, ignore_unavailable=True)
    mapping = {
        'settings': {
            'index': {
                'number_of_shards': '1',
                'number_of_replicas': '0',
                # 'analysis': {
                #     'analyzer': {
                #         'default': {
                #             'filter': ['standard', 'lowercase', 'stop', 'porter_stem'],
                #             'type': 'custom',
                #             'tokenizer': 'standard'
                #         }
                #     }
                # }
            }
        },
        'mappings': {
            'paper': {
                'properties': {
                    'id': {'type': 'keyword'},
                    'title': {'type': 'text'},
                    'paperAbstract': {'type': 'text'},
                    'entities': {'type': 'text'},  # list of str
                    's2Url': {'index': False, 'type': 'keyword'},
                    's2PdfUrl': {'index': False, 'type': 'keyword'},
                    'pdfUrls': {'index': False, 'type': 'keyword'},  # list of urls (str)
                    'authors': {
                        # list of {"name": "John Lee","ids": ["3362353"]}
                        'properties': {
                            'name': {'type': 'text'},
                            'ids': {'type': 'integer'}
                        }
                    },
                    'inCitations': {'type': 'keyword'},  # list of ids (str)
                    'outCitations': {'type': 'keyword'},  # list of ids (str)
                    'year': {'type': 'date', 'format': 'year'},  # int
                    'venue': {'type': 'text'},
                    'journalName': {'type': 'text'},
                    'journalVolume': {'index': False, 'type': 'keyword'},
                    'journalPages': {'index': False, 'type': 'keyword'},
                    'sources': {'type': 'text'},  # list of str
                    'doi': {'type': 'keyword'},  # str, doi w/o http://dx.doi.org
                    'doiUrl': {'index': False, 'type': 'keyword'},  # str, doi w/ http://dx.doi.org
                    'pmid': {'index': False, 'type': 'keyword'},
                }
            }
        }
    }
    es.indices.create(index=es_index, body=mapping)


def gen_actions(es_index):
    def wrapper(item):
        return {
            '_index': es_index,
            '_type': 'paper',
            '_id': item['id'],
            '_source': item
        }
    return wrapper


def gen_data(prep):
    for file in files:
        with open(file, 'r') as f:
            print('Uploading: {}'.format(file))
            for line in f:
                doc = json.loads(line)
                yield prep(doc)


if __name__ == '__main__':
    es = Elasticsearch(
        hosts=[{'host': '172.16.64.23', 'port': 9200}],  # isfet (kibana: 5601)
        use_ssl=False,
        verify_certs=False
    )
    index = 'semantic-scholar'
    buffer_size = 100
    make_index(es, index)
    helpers.bulk(client=es,
                 actions=gen_data(gen_actions(index)),
                 chunk_size=buffer_size)
