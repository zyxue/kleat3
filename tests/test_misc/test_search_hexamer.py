from unittest.mock import MagicMock

import unittest

import kleat.misc.settings as S
from kleat.misc.search_hexamer import (
    plus_search,
    minus_search,
    search,
    extract_seq
)


class TestSearchHexamer(unittest.TestCase):
    def test_plus_search(self):
        self.assertEqual(plus_search('GGGAATAAAG', 9), ('AATAAA', 1, 3))
        self.assertEqual(plus_search('GGGAATAAA', 9), ('AATAAA', 1, 4))
        self.assertEqual(plus_search('GGGAATAAAGG', 9), ('AATAAA', 1, 2))
        self.assertEqual(plus_search('GGGATTAAAGG', 9), ('ATTAAA', 2, 2))
        self.assertEqual(plus_search('GGGAATAA', 9), None)

        self.assertEqual(plus_search('GAATAAAC', 10), ('AATAAA', 1, 4))
        self.assertEqual(plus_search('GGGGCTAC', 20), ('GGGGCT', 16, 13))
        self.assertEqual(plus_search('GTTTATTC', 6), None)

    def test_plus_search_lowercase(self):
        seq = 'GAATaaaC'
        #       4567890
        #             1
        self.assertEqual(plus_search(seq, 10), ('AATAAA', 1, 4))

    def test_plus_search_take_right_most_hexamer(self):
        self.assertEqual(plus_search('CAATAAANAATAAAC', 200), ('AATAAA', 1, 194))

    def test_plus_search_take_right_most_hexamer_with_Ns(self):
        self.assertEqual(plus_search('GCATTAAAAATNAAC', 200), ('ATTAAA', 2, 188))

    def test_plus_search_take_the_strongest_hexamer(self):
        self.assertEqual(plus_search('GCAATAAAATTAAAC', 200), ('AATAAA', 1, 188))

    def test_minus_search(self):
        seq = 'ATTTATTCCC'
        #      90123456789 <- one coord
        #       1          <- ten coord
        self.assertEqual(minus_search(seq, 9), ('AATAAA', 1, 15))
        seq = 'ATTTAATCCC'
        #      90123456789 <- one coord
        #       1          <- ten coord
        self.assertEqual(minus_search(seq, 9), ('ATTAAA', 2, 15))
        self.assertEqual(minus_search('GTTTATTC', 1), ('AATAAA', 1, 7))
        self.assertEqual(minus_search('ATCGTATATTGC', 5), ('AATATA', 7, 14))

    def test_minus_search_lowercase(self):
        self.assertEqual(minus_search('GTttattc', 1), ('AATAAA', 1, 7))

    def test_minus_search_take_left_most_hexamer(self):
        self.assertEqual(minus_search('GTTTATTTTTATTCG', 10), ('AATAAA', 1, 16))

    def test_minus_search_take_left_most_hexamer_with_Ns(self):
        self.assertEqual(minus_search('GTTTATTNTTTATTNNNTGTATTCG', 10), ('AATAAA', 1, 16))

    def test_minus_search_take_the_strongest_hexamer(self):
        self.assertEqual(minus_search('GTTTAATNTTTATTNNNTGTATTCG', 20), ('AATAAA', 1, 33))

    def test_minus_search_take_the_strongest_hexamer_in_lower_case(self):
        self.assertEqual(minus_search('gtttaatntttattnnntgtattcg', 20), ('AATAAA', 1, 33))


class TestSearch(unittest.TestCase):
    def test_plus_strand(self):
        """
         CaataaaGT
        0123456789 <-genome coord
          |      |
          PAS    clv
        """
        seq = 'CaataaaGT'
        clv = 9
        self.assertEqual(search('+', clv, seq, 50), ('AATAAA', 1, 2))

    def test_minus_strand(self):
        """
         GGTTTATT
        0123456789 <-genome coord
         |      |
         clv    PAS
        """
        seq = 'GGTTTATT'
        clv = 1
        self.assertEqual(search('-', clv, seq, 50), ('AATAAA', 1, 8))


class TestExtractSeqForSoftClippedSeq(unittest.TestCase):
    def test_extract_seq_with_starting_softclip(self):
        c = MagicMock()
        c.query_sequence = 'TTCCA'
        c.cigartuples = ((S.BAM_CSOFT_CLIP, 2), (S.BAM_CMATCH, 3))
        assert extract_seq(c) == 'CCA'

    def test_extract_seq_with_ending_softclip(self):
        c = MagicMock()
        c.query_sequence = 'GGGAA'
        c.cigartuples = ((S.BAM_CMATCH, 3), (S.BAM_CSOFT_CLIP, 2))
        assert extract_seq(c) == 'GGG'

    def test_extract_seq_with_both_ends_clipped(self):
        c = MagicMock()
        c.query_sequence = 'TTTGGGAA'
        c.cigartuples = ((S.BAM_CSOFT_CLIP, 3), (S.BAM_CMATCH, 3), (S.BAM_CSOFT_CLIP, 2))
        assert extract_seq(c) == 'GGG'


class TestExtractSeqForHardClippedSeq(unittest.TestCase):
    """The same to the above test, but replaced BAM_CSOFT_CLIP with BAM_CHARD_CLIP"""
    def test_extract_seq_with_starting_softclip(self):
        c = MagicMock()
        c.query_sequence = 'TTCCA'
        c.cigartuples = ((S.BAM_CHARD_CLIP, 2), (S.BAM_CMATCH, 3))
        assert extract_seq(c) == 'CCA'

    def test_extract_seq_with_ending_softclip(self):
        c = MagicMock()
        c.query_sequence = 'GGGAA'
        c.cigartuples = ((S.BAM_CMATCH, 3), (S.BAM_CHARD_CLIP, 2))
        assert extract_seq(c) == 'GGG'

    def test_extract_seq_with_both_ends_clipped(self):
        c = MagicMock()
        c.query_sequence = 'TTTGGGAA'
        c.cigartuples = ((S.BAM_CHARD_CLIP, 3), (S.BAM_CMATCH, 3), (S.BAM_CHARD_CLIP, 2))
        assert extract_seq(c) == 'GGG'
