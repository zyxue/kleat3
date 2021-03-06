from Bio import Seq

import kleat.misc.settings as S


def reverse_complement(seq):
    return str(Seq.Seq(seq).reverse_complement().upper())
    # TODO: if prefer to drop dependency on biopython, test this function
    # thoroughly
    # return seq.translate(COMPLEMENT_DICT)[::-1]


def gen_clv_key_tuple(seqname, strand, clv):
    return (seqname, strand, clv)


def gen_clv_key_tuple_with_ctg_clv(seqname, strand, clv, ctg_clv):
    """
    :param ctg_clv: the clv in contig coordinate
    """
    return (seqname, strand, clv, ctg_clv)


def gen_clv_key_tuple_from_clv_record(clv_record):
    crec = clv_record
    return gen_clv_key_tuple(crec.seqname, crec.strand, crec.clv)


def gen_clv_key_str(seqname, strand, clv):
    return '{seqname}|{strand}|{clv}'.format(**locals())


def fetch_seq(pysam_fa, seqname, beg, end):
    """
    In addition to pysam_fa.fetch, this wrapper handles fetching seq from circular
    DNA (e.g. chrM), too.

    :param pysam_fa: a pysam.libcalignmentfile.AlignmentFile instance
    """
    seq_len = pysam_fa.get_reference_length(seqname)

    circular_contigs = {'chrM', 'MT'}
    if beg <= end:
        if beg >= 0:
            if beg >= seq_len:
                beg -= seq_len
                end -= seq_len
                res = fetch_seq(pysam_fa, seqname, beg, end)
            else:
                if end <= seq_len:
                    res = pysam_fa.fetch(seqname, beg, end)
                else:
                    if seqname in circular_contigs:
                        p1 = pysam_fa.fetch(seqname, beg, seq_len)
                        p2 = pysam_fa.fetch(seqname, 0, end - seq_len)
                        res = p1 + p2
                    else:
                        res = pysam_fa.fetch(seqname, beg, seq_len)
        else:
            if end <= 0:
                beg += seq_len
                end += seq_len
                res = fetch_seq(pysam_fa, seqname, beg, end)
            else:
                if end <= seq_len:
                    if seqname in circular_contigs:
                        p1 = pysam_fa.fetch(seqname, seq_len + beg, seq_len)
                        p2 = pysam_fa.fetch(seqname, 0, end)
                        res = p1 + p2
                    else:
                        res = pysam_fa.fetch(seqname, 0, end)
                else:
                    raise NotImplementedError('How is this possible? Please report'
                                              'seqname: {0}, '
                                              'seq_length: {1}, '
                                              'beg: {2}, '
                                              'end: {3}')
    else:
        beg -= seq_len
        res = fetch_seq(pysam_fa, seqname, beg, end)
    return res


def is_hardclipped(contig):
    for (key, val) in contig.cigartuples:
        if key == S.BAM_CHARD_CLIP:
            return True
    return False


def infer_query_sequence(contig, always=False):
    """
    :param always: mimic pysam api for infer_query_length, by setting always to
    True, it will try to infer sequence with hardclipped region based on XH
    tag. XH tag must exist, otherwise, it would fail loudly

    http://pysam.readthedocs.io/en/latest/api.html#pysam.AlignedSegment.infer_query_length

    """
    res = contig.query_sequence
    if always:
        cgts = contig.cigartuples
        num_cigars = len(cgts)
        for k, (key, val) in enumerate(cgts):
            if key != S.BAM_CHARD_CLIP:
                continue

            if k == 0:
                res = contig.get_tag('XH') + res
            elif k == num_cigars - 1:
                res += contig.get_tag('XH')
            else:
                err_msg = ("it seems there is a hardclip in the middle "
                           "of the contig, which was thought to be impossible"
                           "please report by opening a new github issue")
                raise ValueError(err_msg)
    return res


"""
Below are utility functions that apply to both contig and read as long as
they have a tail
"""


def right_tail(segment, tail_base='A'):
    """
    tseg: tail segment
    default tail_base applies main to alignment to genome, where the polyA tail
    strand is known
    """
    seq = segment.query_sequence
    last_cigar = segment.cigartuples[-1]
    return (
        seq.endswith(tail_base)
        # right clipped
        and last_cigar[0] == S.BAM_CSOFT_CLIP
        # clipped are all As
        and set(seq[-last_cigar[1]:]) == {tail_base}
    )


def left_tail(segment, tail_base='T'):
    seq = segment.query_sequence
    first_cigar = segment.cigartuples[0]
    return (
        seq.startswith(tail_base)
        # left clipped
        and first_cigar[0] == S.BAM_CSOFT_CLIP
        # clipped are all Ts
        and set(seq[:first_cigar[1]]) == {tail_base}
    )


def has_tail(segment):
    if left_tail(segment):
        return 'left'
    elif right_tail(segment):
        return 'right'
    else:
        return None


def calc_tail_length(suffix_segment, tail_side=None):
    """
    Calculate A/T length of a contig or a read, this information is extracted
    from softclip in the CIGAR
    """
    if tail_side is None:
        tail_side = has_tail(suffix_segment)

    if tail_side == 'left':
        the_cigar = suffix_segment.cigartuples[0]
    elif tail_side == 'right':
        the_cigar = suffix_segment.cigartuples[-1]
    else:
        raise ValueError('{0} is not a suffix segment'.format(suffix_segment))

    if the_cigar[0] != S.BAM_CSOFT_CLIP:
        cigar_idx = 'first' if tail_side == 'left' else 'last'
        raise ValueError('this may not be a {0} tailed segment as its '
                         '{1} CIGAR is not BAM_CSOFT_CLIP ({2})'.format(
                             tail_side, cigar_idx, S.BAM_CSOFT_CLIP))
    return the_cigar[1]


def write_row(clv_record, csvwriter):
    csvwriter.writerow([getattr(clv_record, _) for _ in S.HEADER])
