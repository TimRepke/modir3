## all_docs.csv
All docs contains all the docs that contain "Sustainab*" in the title, abstract
or keywords, that we could obtain from the web of science.

From the web of science we obtain the fields
- `authors`
- `first_author`
- `PY` (publication year)
- `content` (the abstract of the article)
- `title`
- `wosarticle__de` (author defined keywords)
- `wosarticle__wc` (web of science defined areas of study)

Additional columns:
- `id` - the unique ID of the document in our database
- `ratings` - the number of times the document was rated
- `majority_rating` - the majority rating. If the document has not been rated:
NaN, if there is no majority: 3, if the majority rated relevant: 1, if the majority rated irrelevant: 0
- `rating_[n]` - the rating by the user with the ID `n`, if there is one
- `tags` - describes the context in which the ratings were made. Most lots of
annotations were randomly selected, but some were selected based on an early model,
to show users uncertain, or irrelevant documents. This should be clear from the tag names.

## Ambiverse
Please check data_preparation/ambiverse.py to see how we enriched the dataset with named entities.

## Load with Pandas:
```python
import pandas as pd
from datetime import datetime
import ast
import re
df = pd.read_csv('data/mcc/all_docs.csv', header=0, index_col='id', na_filter=False,
                 parse_dates=['PY'], date_parser=lambda s: datetime.strptime(s, '%Y.0'),
                 converters={'wosarticle__de': lambda s: s.split(';'),
                             'wosarticle__wc': lambda s: ast.literal_eval(s),
                             'tags': lambda s: re.sub(r'\d{4}-\d\d-\d\d \d\d:\d\d','', s).split(';'),
                             'authors': lambda s: [f'{a1.strip()} {a0.strip()}' for a0, a1 in zip(s.split(',')[0::2], s.split(',')[1::2])],
                             'first_author': lambda s: ' '.join(reversed(s.split(',')))})
```

## Get subset from elasticsearch
```bash
curl -s 'http://isfet:5601/elasticsearch/_msearch?rest_total_hits_as_int=true&ignore_throttled=true' \
     -H 'Origin: http://isfet:5601' \
     -H 'Accept-Encoding: gzip, deflate' \
     -H 'Accept-Language: en-GB,en;q=0.9,de-DE;q=0.8,de;q=0.7' \
     -H 'kbn-version: 6.6.1' \
     -H 'content-type: application/x-ndjson' \
     -H 'Accept: application/json, text/plain, */*' \
     -H 'Referer: http://isfet:5601/app/kibana' \
     --data-binary $'{"index":"mcc","ignore_unavailable":true,"preference":1552473936116}\n{"version":true,"size":3,"query":{"bool":{"must":[{"query_string":{"query":"germany","analyze_wildcard":true,"default_field":"*"}}], "filter":[],"should":[],"must_not":[]}}}\n' \
     --compressed | jq -c '.responses[0].hits.hits[]._source' > mcc_germany.json
```
