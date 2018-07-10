import kleat.misc.settings as S


def gen_clv_key_tuple(seqname, strand, clv):
    return (seqname, strand, clv)


def gen_clv_key_tuple_from_clv_record(clv_record):
    crec = clv_record
    return gen_clv_key_tuple(crec.seqname, crec.strand, crec.clv)


def gen_clv_key_str(seqname, strand, clv):
    return '{seqname}|{strand}|{clv}'.format(**locals())


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
            if cur_ctg_ofs >= ctg_offset:
                # this means that the clv happens to be in the middle of the
                # inserted sequence
                if tail_direction == 'left':
                    break
                elif tail_direction == 'right':
                    # jump to the next position in genome coordinate
                    cur_gnm_ofs += 1
                    break
                else:
                    err_msg = ('tail_direction must be "left" or "right", '
                               'but received {0}'.format(tail_direction))
                    raise ValueError(err_msg)
        else:
            pass
            # Not sure about S.BAM_CPAD & BAM_CBACK,
            # please let me know if you do
    return cur_gnm_ofs


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
    # potential test case == "A0.R100820":
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
    # potential test case A0.S36384
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


def calc_ref_clv(suffix_segment, tail_side=None):
    """
    Calculate cleavage site position wst the reference

    :param tail_sideed: pass to avoid redundant checking of tail
    """
    if tail_side is None:
        tail_side = has_tail(suffix_segment)

    # the coordinates (+1 or not) are verified against visualization on IGV
    if tail_side == 'left':
        return suffix_segment.reference_start
    elif tail_side == 'right':
        return suffix_segment.reference_end - 1
    else:
        raise ValueError('{0} is not a suffix segment'.format(suffix_segment))


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


def calc_strand_from_suffix_segment(suffix_segment):
    """
    calculate the strand of clv (hence the corresponding gene) from a suffix
    segment
    """
    tail_side = has_tail(suffix_segment)
    if tail_side is None:
        raise ValueError('{0} is not a suffix segment, hence strand cannot be '
                         'inferred'.format(suffix_segment))
    return calc_strand(tail_side)


def calc_strand(tail_side):
    if tail_side == 'left':
        return '-'
    elif tail_side == 'right':
        return '+'
    else:
        raise ValueError('tail_side must be "left" or "right", '
                         'but {0} passed'.format(tail_side))


def write_row(clv_record, csvwriter):
    csvwriter.writerow([getattr(clv_record, _) for _ in S.HEADER])
