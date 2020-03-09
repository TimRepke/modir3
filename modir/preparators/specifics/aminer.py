from .papers import PaperGensimProcessor


class AminerGensimProcessor(PaperGensimProcessor):

    def _generate_docs(self):
        # index ---- index id of this paper
        # * ---- paper title
        # @ ---- authors (separated by semicolons)
        # o ---- affiliations (separated by semicolons, and each affiliation corresponds to an author in order)
        # t ---- year
        # c ---- publication venue
        # % ---- the id of references of this paper (there are multiple lines, with each indicating a reference)
        # ! ---- abstract
        with open(self.in_file, 'r') as f:
            index = 0
            doc = {}
            for line in f:
                line = line.strip()
                if len(line) == 0:
                    yield doc
                    index += 1
                    doc = {}
                else:
                    if line[:6] == '#index':
                        doc[self.ID_KEY] = line[7:]
                    elif line[:2] == '#*':
                        doc[self.TITLE_KEY] = line[3:]
                    elif line[:2] == '#@':
                        doc['authors'] = line[3:].split(';')
                    elif line[:2] == '#o':
                        doc['affiliations'] = line[3:].split(';')
                    elif line[:2] == '#t':
                        doc['year'] = line[3:]
                    elif line[:2] == '#c':
                        doc[self.VENUE_KEY] = line[3:]
                    elif line[:2] == '#%':
                        if 'references' not in doc:
                            doc['references'] = []
                        doc['references'].append(line[3:])
                    elif line[:2] == '#!':
                        doc[self.TEXT_KEY] = line[3:]
            print(f'Yielded {index + 1} documents!')
