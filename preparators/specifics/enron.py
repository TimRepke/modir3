from ..gensim_processor import GensimProcessor
from xml.sax.saxutils import unescape
from lxml import etree


class EnronGensimProcessor(GensimProcessor):
    def __init__(self, only_original, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.only_original = only_original

    def _generate_docs(self):
        index = 0
        for event, elem in etree.iterparse(self.in_file):
            if elem.text == 'email':
                parent = elem.getparent()
                try:
                    doc = {
                        self.ID_KEY: int(parent.get('id')),
                        'is_original': True,
                        self.TEXT_KEY: ''
                    }
                    for sibling in parent:
                        if sibling.get('key') == 'text':
                            doc[self.TEXT_KEY] = unescape(sibling.text or '').strip()
                            # TODO try fallback to duplicate if text empty?
                        elif sibling.get('key') == 'subject':
                            doc[self.TITLE_KEY] = sibling.text
                        elif sibling.get('key') == 'sent':
                            doc['sent'] = sibling.text
                        elif sibling.get('key') == 'block_type':
                            doc['block_type'] = sibling.text
                        elif sibling.get('key') == 'labelV':
                            doc['is_original'] = sibling.text == 'email'
                        elif sibling.get('key') == 'original':
                            doc['original_id'] = int(sibling.text)
                        sibling.clear()
                    parent.clear()

                    if self.only_original and not doc['is_original']:
                        continue

                    yield doc
                    index += 1
                except TypeError as e:
                    if str(e) != "int() argument must be a string, a bytes-like object or a number, not 'NoneType'":
                        print(e)
                except AttributeError as e:
                    print(e)
            elem.clear()
        print(f'Yielded {index + 1} documents!')
