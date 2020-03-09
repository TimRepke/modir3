from tqdm import tqdm
import requests
import json

with open('../../data/news/coba_news.json', 'r') as f, open('../../data/news/coba_news_amb.json', 'a') as ff:
    pbar = tqdm(enumerate(f))
    for i, line in pbar:
        try:
            doc = json.loads(line)
            pbar.set_description(f"{doc['published']} || {len(doc['article'])} || {doc['title']}")
            if i < 15:
                continue
            res = requests.post('https://ambiversenlu.mpi-inf.mpg.de/wp-admin/admin-ajax.php',
                                data={'action': 'tag_analyze_document',
                                      'text': doc['article'],
                                      'coherentDocument': True,
                                      'extractConcepts': True,
                                      'confidenceThreshold': 0.075,
                                      'language': 'auto',
                                      'apiEndpoint': 'api',
                                      'apiMethod': '/entitylinking/',
                                      '_ajax_nonce': '814952e981'
                                      })
            amb = json.loads(res.text)
            doc['entities'] = amb['entities']
            doc['matches'] = amb['matches']
            doc['language'] = amb['language']

            ff.write(json.dumps(doc) + '\n')
        except Exception as e:
            print(e)


# category
# color (hex ohne raute)
