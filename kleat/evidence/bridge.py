from collections import defaultdict

from kleat.misc import apautils
import kleat.misc.settings as S


def write_evidence(dd_bridge, contig, csvwriter):
    for clv_key in dd_bridge['num_reads']:
        clv_record = gen_clv_record(
            contig, clv_key,
            dd_bridge['num_reads'][clv_key],
            dd_bridge['max_tail_len'][clv_key]
        )
        apautils.write_row(clv_record, csvwriter)


def update_evidence(evid_tuple, evid_holder):
    """
    update the bridge evidence holder with extracted bridge evidence

    :param evid_tuple: evidence tuple
    :param evid_holder: A dict holder bridge evidence for a given contig
    """
    seqname, strand, ref_clv, tail_len = evid_tuple
    clv_key = apautils.gen_clv_key_tuple(seqname, strand, ref_clv)
    evid_holder['num_reads'][clv_key] += 1
    evid_holder['max_tail_len'][clv_key] = max(
        evid_holder['max_tail_len'][clv_key], tail_len)


def is_a_bridge_read(read):
    return not read.is_unmapped and apautils.has_tail(read)


def init_evidence_holder():
    """
    initialize holders for bridge and link evidence of a given contig
    """
    return {
        'num_reads': defaultdict(int),
        'max_tail_len': defaultdict(int),
    }


def calc_genome_offset(ctg_cigartuples, ctg_offset, tail_direction):
    """
    Calculate the offset needed for inferring the clv in genomic coordinate

    Offset needs taking into oconsideration the skipped region caused by intron
    or deletion

    :param ctg_offset: the offset calculated based on clv in contig coordinate.
    ctg_offset is always forward. If the contig is reversed, its value is still
    based based forward coordinates of this contig. See the following test
    cases for details in test_bridge.py

    test_do_forwad_contig_left_tail_brdige_read()
    test_do_forwad_contig_right_tail_brdige_read()
    test_do_reverse_contig_left_tail_brdige_read()
    test_do_reverse_contig_right_tail_brdige_read()
    """
    cur_ctg_ofs = 0             # curent offset in contig coordinate
    cur_gnm_ofs = 0             # current offset in genome coordinate
    for key, val in ctg_cigartuples:
        if key in [S.BAM_CMATCH, S.BAM_CEQUAL, S.BAM_CDIFF]:
            cur_ctg_ofs += val
            if cur_ctg_ofs >= ctg_offset:
                delta = val - (cur_ctg_ofs - ctg_offset)
                cur_gnm_ofs += delta
                break
            cur_gnm_ofs += val
        elif key in [S.BAM_CREF_SKIP, S.BAM_CDEL]:
            cur_gnm_ofs += val
        elif key in [S.BAM_CINS, S.BAM_CSOFT_CLIP, S.BAM_CHARD_CLIP]:
            # these don't consume reference coordinates, but consumes contig
            # coordinates, so needs subtraction
            ctg_offset -= val
            if cur_ctg_ofs > ctg_offset:
                break
        else:
            pass
            # Not sure about S.BAM_CPAD & BAM_CBACK,
            # please let me know if you do
    return cur_gnm_ofs


def do_fwd_ctg_lt_bdg(read):
    """fwd: forwad, ctg: contig, lt: left-tailed, bdg: bridge"""
    return '-', read.reference_start + 1, read.cigartuples[0][1]


def do_fwd_ctg_rt_bdg(read):
    """rt: right-tailed"""
    return '+', read.reference_end, read.cigartuples[-1][1]


def do_rev_ctg_lt_bdg(read, ctg_len):
    # rev (reverse), opposite of fwd (forward)
    return '+', ctg_len - read.reference_start, read.cigartuples[0][1]


def do_rev_ctg_rt_bdg(read, ctg_len):
    return '-', ctg_len - read.reference_end + 1, read.cigartuples[-1][1]


def do_forward_contig(contig, read):
    if apautils.left_tail(read, 'T'):
        return do_fwd_ctg_lt_bdg(read) + ('left', )
    elif apautils.right_tail(read, 'A'):
        return do_fwd_ctg_rt_bdg(read) + ('right', )
    else:
        raise ValueError('no tail found for read {0}'.format(read))


def do_reverse_contig(contig, read):
    # set always=True to include hard-clipped bases
    # https://pysam.readthedocs.io/en/latest/api.html?highlight=parse_region#pysam.AlignedSegment.infer_query_length
    ctg_len = contig.infer_query_length(always=True)
    # TODO: avoid multiple calling of left_tail/right_tail
    if apautils.left_tail(read, 'T'):
        return do_rev_ctg_lt_bdg(read, ctg_len) + ('left',)
    elif apautils.right_tail(read, 'A'):
        return do_rev_ctg_rt_bdg(read, ctg_len) + ('right',)
    else:
        raise ValueError('no tail found for read {0}'.format(read))


def do_bridge(contig, read):
    if contig.is_reverse:
        return do_reverse_contig(contig, read)
    else:
        return do_forward_contig(contig, read)


def analyze_bridge(contig, read):
    seqname = contig.reference_name

    print(do_bridge(contig, read))
    strand, ctg_offset, tail_len, tail_direction = do_bridge(contig, read)
    offset = calc_genome_offset(contig.cigartuples, ctg_offset, tail_direction)
    gnm_clv = contig.reference_start + offset

    return seqname, strand, gnm_clv, tail_len


def gen_clv_record(
        bridge_contig, clv_key_tuple, num_bridge_reads, max_bridge_tail_len):
    seqname, strand, gnm_clv = clv_key_tuple
    return S.ClvRecord(
        seqname, strand, gnm_clv,

        'bridge',
        bridge_contig.query_name,
        bridge_contig.infer_query_length(True),
        bridge_contig.mapq,

        0,                      # num_tail_reads
        0,                      # tail_length

        num_bridge_reads,
        max_bridge_tail_len,

        num_link_reads=0,
        num_blank_contigs=0
    )
