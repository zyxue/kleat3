from collections import defaultdict
from unittest.mock import MagicMock

import pytest

from kleat.evidence import bridge
from kleat.misc.settings import (
    BAM_CMATCH, BAM_CDEL, BAM_CREF_SKIP,
    BAM_CINS, BAM_CSOFT_CLIP, BAM_CHARD_CLIP)


def test_bridge_init_evidence_holder():
    assert bridge.init_evidence_holder() == {
        'num_reads': defaultdict(int),
        'max_tail_len': defaultdict(int),
    }


@pytest.mark.parametrize("ctg_cigartuples, ctg_offset_cutoff, gnm_offset", [
    [((BAM_CMATCH, 10),), 2, 2],
    [((BAM_CMATCH, 20),), 5, 5],
])
def test_calc_genome_offset_for_nonskipped_contig(
        ctg_cigartuples, ctg_offset_cutoff, gnm_offset):
    assert bridge.calc_genome_offset(ctg_cigartuples, ctg_offset_cutoff) == gnm_offset


@pytest.mark.parametrize("ctg_cigartuples, ctg_offset_cutoff, gnm_offset", [
    # ctg_offset_cutoff before skip happens
    [((BAM_CMATCH, 10), (BAM_CREF_SKIP, 5), (BAM_CMATCH, 10)), 2, 2],
    # ctg_offset_cutoff after skip happens
    [((BAM_CMATCH, 10), (BAM_CREF_SKIP, 5), (BAM_CMATCH, 10)), 12, 17],
])
def test_calc_genome_offset_for_skipped_contig(
        ctg_cigartuples, ctg_offset_cutoff, gnm_offset):
    assert bridge.calc_genome_offset(ctg_cigartuples, ctg_offset_cutoff) == gnm_offset

@pytest.mark.parametrize("ctg_cigartuples, ctg_offset_cutoff, gnm_offset", [
    [((BAM_CMATCH, 31), (BAM_CDEL, 2), (BAM_CMATCH, 44)), 5, 5],
    [((BAM_CMATCH, 31), (BAM_CDEL, 2), (BAM_CMATCH, 44)), 31, 31],
    [((BAM_CMATCH, 31), (BAM_CDEL, 2), (BAM_CMATCH, 44)), 32, 34],
    [((BAM_CMATCH, 31), (BAM_CDEL, 2), (BAM_CMATCH, 44)), 33, 35],
])
def test_calc_genome_offset_for_skipped_contig_with_deletion(
        ctg_cigartuples, ctg_offset_cutoff, gnm_offset):
    assert bridge.calc_genome_offset(ctg_cigartuples, ctg_offset_cutoff) == gnm_offset


@pytest.mark.parametrize("ctg_offset_cutoff, expected_gnm_offset", [
    [2, 2],                # before the insertion, see example in the docstring
    [7, 4],                # after the insertion

    # If the polyA/T tail starts inside the inserted sequence, use the lowest
    # genome coordinate to represent clv. Ideally strand (A or T) could also be
    # considered, but that requires more information passed to
    # calc_genome_offset for now (TODO).
    [4, 3],
    [5, 3],
    [6, 3],
])
def test_calc_genome_offset_for_skipped_contig_with_insertion(ctg_offset_cutoff, expected_gnm_offset):
    """
       AGC  <-inserted sequence
       456  <-contig coord for inserted sequence
        ┬
     XXX XX <-contig
    0123 78 <-contig coord
    0123 45 <-genome offset
    """
    ctg_cigartuples = ((BAM_CMATCH, 3), (BAM_CINS, 3), (BAM_CMATCH, 2))
    assert bridge.calc_genome_offset(ctg_cigartuples, ctg_offset_cutoff) == expected_gnm_offset


@pytest.mark.parametrize("ctg_offset_cutoff, expected_gnm_offset", [
    [2, 0],                   # overlap with clv extracted from suffix evidence
    [3, 1],                   # bridge tail is a bit after the contig tail
])
def test_calc_genome_offset_for_skipped_contig_with_softclip(ctg_offset_cutoff, expected_gnm_offset):
    """
     TT
     01
      └XXX <-contig
       234 <-contig coord
       012 <-genome offset
    """
    ctg_cigartuples = ((BAM_CSOFT_CLIP, 2), (BAM_CMATCH, 3))
    assert bridge.calc_genome_offset(ctg_cigartuples, ctg_offset_cutoff) == expected_gnm_offset


def get_mock_read(reference_start, reference_end, cigartuples):
    r = MagicMock()
    r.reference_start = reference_start
    r.reference_end = reference_end
    r.cigartuples = cigartuples
    return r


def test_do_forwad_contig_left_tail_brdige_read():
    """
    e.g. TTTACG, reference_start at 2 points to the position of the first T
    (based on IGV)

     TTT
       └ACG  <-left-tail read
      XXACGX <-contig
     0123456 <-contig coord
    """
    mock_read = get_mock_read(2, 5, [(BAM_CSOFT_CLIP, 3), (BAM_CMATCH, 3)])
    ctg_offset = 3          # 2 + 1
    tail_len = 3
    assert bridge.do_fwd_ctg_lt_bdg(mock_read) == ('-', ctg_offset, tail_len)


def test_do_forwad_contig_left_tail_brdige_read_2():
    """
    e.g. TTAATTCCGG
    """
    mock_read = get_mock_read(10, 18, [(BAM_CSOFT_CLIP, 2), (BAM_CMATCH, 8)])
    ctg_offset = 11         # 10 + 1
    tail_len = 2
    assert bridge.do_fwd_ctg_lt_bdg(mock_read) == ('-', ctg_offset, tail_len)


def test_do_forwad_contig_right_tail_brdige_read():
    """
    e.g. CCGGAA, reference_end at 4 points to the position of G (based on IGV)

          AA
       CCG┘  <-right-tail read
      XCCGXX <-contig
     0123456 <-contig coord
    """
    mock_read = get_mock_read(1, 4, [(BAM_CMATCH, 4), (BAM_CSOFT_CLIP, 2)])
    ctg_offset = 4
    tail_len = 2
    assert bridge.do_fwd_ctg_rt_bdg(mock_read) == ('+', ctg_offset, tail_len)


def test_do_reverse_contig_left_tail_brdige_read():
    """
    e.g. TTTACG
     TTT
       └ACG  <-left-tail read
      XXACGX <-contig
     0123456 <-contig coord
      6543210<-contig coord after reverse
    """
    mock_read = get_mock_read(2, 5, [(BAM_CSOFT_CLIP, 3), (BAM_CMATCH, 3)])
    # in genome coordinates, it's reversed, the the clv points to the position
    # of A, while position 0 point to the position after G.
    contig_len = 6
    ctg_offset = 4
    tail_len = 3
    assert bridge.do_rev_ctg_lt_bdg(mock_read, contig_len) == ('+', ctg_offset, tail_len)


def test_do_reverse_contig_right_tail_brdige_read():
    """
    e.g. CCGGAA, reference_end at 4 points to the position of G (based on IGV)

          AA
       CCG┘  <-right-tail read
      XCCGXX <-contig
     0123456 <-contig coord
      6543210<-contig coord after reverse
    """
    mock_read = get_mock_read(1, 4, [(BAM_CSOFT_CLIP, 3), (BAM_CMATCH, 2)])
    # in genome coordinates, it's reversed, the the clv points to the position
    # of A, while position 0 point to the position after G.
    contig_len = 6
    ctg_offset = 3
    tail_len = 2
    assert bridge.do_rev_ctg_rt_bdg(mock_read, contig_len) == ('-', ctg_offset, tail_len)
