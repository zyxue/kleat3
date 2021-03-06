from collections import defaultdict
from unittest.mock import MagicMock

from kleat.evidence import bridge
from kleat.evidence.do_bridge import (
    do_fwd_ctg_lt_bdg, do_fwd_ctg_rt_bdg,
    do_rev_ctg_lt_bdg, do_rev_ctg_rt_bdg
)

import kleat.misc.settings as S


def test_bridge_init_evidence_holder():
    assert bridge.init_evidence_holder() == {
        'num_reads': defaultdict(int),
        'max_tail_len': defaultdict(int),
        'hexamer_tuple': defaultdict(lambda: None),
    }


def get_mock_read(ref_beg, ref_end, cigartuples):
    r = MagicMock()
    r.reference_start = ref_beg
    r.reference_end = ref_end
    r.cigartuples = cigartuples
    return r


def test_do_fwd_ctg_lt_bdg():
    """e.g. TTTACG, reference_start at pos 2 (0-based) with the first three Ts
    soft-clipped

    compared to igv visualization, which is 1-based, the contig coord are
    shifted to the right by one-base, a quick comparison is available at
    http://zyxue.github.io/2018/06/21/coordinates-in-bioinformatics.html

    TTT
      └ACG    <-left-tail read
     XXACGXX  <-contig
     0123456  <-contig coord
     0123456  <-genome coord offset to 0
       ^ctg_offset
    """
    mock_read = get_mock_read(
        ref_beg=2, ref_end=5,
        cigartuples=[(S.BAM_CSOFT_CLIP, 3), (S.BAM_CMATCH, 3)]
    )
    mock_contig = MagicMock()
    mock_contig.infer_query_length.return_value = 7
    mock_contig.cigartuples = ((S.BAM_CMATCH, 7),)
    # basically the clv wst. to the contig coordinate when in forward contig
    ctg_offset = 2
    tail_len = 3
    assert do_fwd_ctg_lt_bdg(mock_read, contig=mock_contig) == ('-', ctg_offset, tail_len)


def test_do_fwd_ctg_lt_bdg_2():
    """
    TT
    |└AATTCCGG   <-left-tail read
    XXAATTCCGGXX <-contig
    890123456789 <-contig coord
    890123456789 <-genome coord offset to 0
      1
      ^ctg_offset
    """
    mock_read = get_mock_read(
        ref_beg=10, ref_end=18, cigartuples=[(S.BAM_CSOFT_CLIP, 2), (S.BAM_CMATCH, 8)])

    mock_contig = MagicMock()
    mock_contig.infer_query_length.return_value = 12
    mock_contig.cigartuples = ((S.BAM_CMATCH, 12),)

    ctg_offset = 10
    tail_len = 2
    assert do_fwd_ctg_lt_bdg(mock_read, contig=mock_contig) == ('-', ctg_offset, tail_len)


def test_do_fwd_ctg_rt_bdg():
    """
        AA
     CCG┘      <-right-tail read
    XXCCGXX    <-contig
    0123456    <-contig coord
    0123456    <-genome coord offset to 0
       ^ctg_offset
    """
    mock_read = get_mock_read(
        ref_beg=1, ref_end=4, cigartuples=[(S.BAM_CMATCH, 3), (S.BAM_CSOFT_CLIP, 2)])

    mock_contig = MagicMock()
    mock_contig.infer_query_length.return_value = 7
    mock_contig.cigartuples = ((S.BAM_CMATCH, 7),)

    ctg_offset = 3
    tail_len = 2
    assert do_fwd_ctg_rt_bdg(mock_read, contig=mock_contig) == ('+', ctg_offset, tail_len)


def test_do_rev_ctg_lt_bdg():
    """
           TTT
            |└ACG   <-left-tail read
            XXACGXX <-contig
            0123456 <-contig coord
            6543210 <-reversed genome coord offset to 0
    ctg_offset^
    """
    mock_read = get_mock_read(
        ref_beg=2, ref_end=5, cigartuples=[(S.BAM_CSOFT_CLIP, 3), (S.BAM_CMATCH, 3)])
    # in genome coordinates, it's reversed, the the clv points to the position
    # of A, while position 0 point to the position after G.
    contig = MagicMock()
    contig.infer_query_length.return_value = 7

    ctg_offset = 4
    tail_len = 3
    assert do_rev_ctg_lt_bdg(mock_read, contig=contig) == ('+', ctg_offset, tail_len)


def test_do_rev_ctg_rt_bdg():
    """
               AA
            CCG┘|  <-right-tail read
           XXCCGXX <-contig
           0123456 <-contig coord
           6543210 <-reversed genome coord offset to 0
    ctg_offset^
    """
    mock_read = get_mock_read(
        ref_beg=1, ref_end=4, cigartuples=[(S.BAM_CSOFT_CLIP, 3), (S.BAM_CMATCH, 2)])
    # in genome coordinates, it's reversed, the the clv points to the position
    # of A, while position 0 point to the position after G.
    contig = MagicMock()
    contig.infer_query_length.return_value = 7
    ctg_offset = 3
    tail_len = 2
    assert do_rev_ctg_rt_bdg(mock_read, contig=contig) == ('-', ctg_offset, tail_len)
