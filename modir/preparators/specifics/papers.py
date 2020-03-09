from abc import ABC
from ..gensim_processor import GensimProcessor


class PaperGensimProcessor(GensimProcessor, ABC):
    VENUE_MAP = {
        'DB': ['VLDB', 'SIGMOD', 'ICDE', 'EDBT'],
        'ML': ['NIPS', 'AAAI', 'ICML', 'CAI'],
        'DM': ['KDD', 'ICDM', 'CIKM', 'WSDM'],
        'ComLing': ['EMNLP', 'ACL', 'CoNLL', 'COLING'],
        'CompVis': ['CVPR', 'ICCV', 'ICIP', 'SIGGRAPH', 'Computer Vision'],
        'HCI': ['CHI', 'IUI', 'UIST', 'CSCW', 'CogSci', 'Cognitive Science']
    }
    UNDEFINED_COMMUNITY = 'Other'
    COMMUNITY_KEY = 'community'
    VENUE_KEY = 'venue'

    def __init__(self, filter_venue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_venue = filter_venue

    def _venue2community(self, venue: str) -> str:
        for community, venues in self.VENUE_MAP.items():
            for venue_ in venues:
                # if venue_.upper() in venue.upper():
                if venue_ in venue:
                    return community
        return self.UNDEFINED_COMMUNITY
