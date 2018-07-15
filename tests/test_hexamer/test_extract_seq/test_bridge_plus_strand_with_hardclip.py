from unittest.mock import MagicMock, patch

import kleat.misc.settings as S
from kleat.hexamer.search import extract_seq


# @patch('kleat.hexamer.search.apautils')
# def test_hardclip_before_clv(mock_apautils):
#     """
#            AA
#          TC┘         <-bridge read
#     CGCATTCGTCG      <-bridge contig (hardcipped, could be chimeric https://www.biostars.org/p/109333/)
#     \\\|  |          <-hardclip mask
#     01234567890      <-contig coord
#        |cc^   ^ice
#     ...ATTCGTCG...   <-genome
#        567890123     <-genome coord
#           | 1 |
#         rc^   ^ire
#     """
#     ctg = MagicMock()
#     ctg.reference_name = 'chr2'
#     mock_apautils.infer_query_sequence.return_value = 'CGCATTCGTCG'
#     ctg.cigartuples = ((S.BAM_CHARD_CLIP, 3), (S.BAM_CMATCH, 8))

#     ref_fa = MagicMock()
#     ref_fa.get_reference_length.return_value = 100
#     kw = dict(contig=ctg, strand='+', ref_clv=8, ref_fa=ref_fa, ctg_clv=6)
#     assert extract_seq(**kw) == 'CGCATTC'
#     assert extract_seq(window=3, **kw) == 'TTC'


@patch('kleat.hexamer.search.apautils')
def test_extract_hardclip_after_clv(mock_apautils):
    """
             AAA
          GTT┘                 <-bridge read
       A-GGTTGCAGA             <-bridge contig
       | |  | |///             <-hardclip mask
       0 1234567890            <-contig coord
     ctg_clv^     ^ice <-contig coord
    ...ACGGTTGCAGA...          <-genome
       789012345678            <-genome coord
          1 |     |
     ref_clv^     ^init_fe
    """
    ctg = MagicMock()
    ctg.reference_name = 'chr1'
    mock_apautils.infer_query_sequence.return_value = 'AGGTTGCAGA'
    ctg.cigartuples = (
        (S.BAM_CMATCH, 1),
        (S.BAM_CREF_SKIP, 1),
        (S.BAM_CMATCH, 6),
        (S.BAM_CHARD_CLIP, 3)
    )

    ref_fa = MagicMock()
    ref_fa.get_reference_length.return_value = 100
    ref_fa.fetch = MagicMock(return_value='C')
    kw = dict(contig=ctg, strand='+', ref_clv=12, ref_fa=ref_fa, ctg_clv=4)
    assert extract_seq(**kw) == 'ACGGTT'
    # assert extract_seq(window=3, **kw) == 'TGC'
    # ref_fa.fetch.assert_called_with('chr1', 11, 13)
