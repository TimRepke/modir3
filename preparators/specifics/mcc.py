from ..gensim_processor import GensimProcessor
from ..hypergraph import HyperGraph
import ujson as json


class MCCGensimProcessor(GensimProcessor):

    def _generate_docs(self):
        with open(self.in_file, 'r') as f:
            index = 0
            for line in f:
                doc = json.loads(line)

                doc[self.ID_KEY] = doc['url']
                doc[self.TEXT_KEY] = doc.get('content', '')
                if self.TEXT_KEY != 'content':
                    del doc['content']

                yield doc
                index += 1
            print(f'Yielded {index + 1} documents!')


