import matplotlib.patches as patches

import numpy as np
import pandas as pd

import kleat.misc.settings as S


"""
Every position should be in the same direction as reference genome
"""


CIGAR_EVENTS_COLOR_DD = {
    S.BAM_CMATCH: 'green',       # 0
    S.BAM_CSOFT_CLIP: 'orange',  # 4
    S.BAM_CHARD_CLIP: 'red',     # 5

    S.BAM_CREF_SKIP: 'black',    # 3
    S.BAM_CDEL: 'blue',          # 2

    S.BAM_CINS: 'cyan',          # 1
}

CIGAR_EVENTS_HEIGHT_DD = {
    S.BAM_CMATCH: 0.7,       # 0
    S.BAM_CSOFT_CLIP: 0.9,   # 4
    S.BAM_CHARD_CLIP: 0.9,   # 5
    # S.BAM_CDEL: 0.08,         # 2
    # S.BAM_CINS: 0.08,         # 1
    # S.BAM_CREF_SKIP: 'black',
}


def make_line(ax, cx, cy, width, color='black'):
    xs = [cx, cx + width]
    ys = [cy, cy]
    line = ax.plot(xs, ys, ':', color=color)
    return line


def make_box(ax, cx, cy, width, height, facecolor):
    pat = patches.Rectangle(
        (cx, cy),
        width, height,
        facecolor=facecolor,
        edgecolor='white')
    ax.add_patch(pat)
    return pat


def annot_box(ax, patch, txt):
    pass
    # pat_x = patch.get_x() + patch.get_width() / 2.0
    # pat_y = patch.get_y() + patch.get_height() / 2.0
    # return ax.annotate(
    #     txt, (pat_x, pat_y),
    #     color='w', weight='bold', fontsize=8,
    #     ha='center', va='center'
    # )


def draw_box(ax, cx, cy, cigartuple):
    key, val = cigartuple
    width = val
    height = CIGAR_EVENTS_HEIGHT_DD[key]
    color = CIGAR_EVENTS_COLOR_DD[key]

    cy = cy - height * 0.5
    return make_box(ax, cx, cy, width, height, color)


def draw_match(ax, cx, cy, cigartuple):
    patch = draw_box(ax, cx, cy, cigartuple)
    annot_box(ax, patch, 'M')


def draw_softclip(ax, cx, cy, cigartuple):
    patch = draw_box(ax, cx, cy, cigartuple)
    annot_box(ax, patch, 'SC')


def draw_hardclip(ax, cx, cy, cigartuple):
    patch = draw_box(ax, cx, cy, cigartuple)
    annot_box(ax, patch, 'HC')


def draw_skip(ax, cx, cy, cigartuple):
    key, val = cigartuple
    make_line(ax, cx, cy, width=val)
    # val = cigartuple[1]
    # ax.text(x + val * 0.5, y - 0.01,
    #         f'skip-{val}bp',
    #         va='top', ha='center', rotation=90)


def draw_del(ax, cx, cy, cigartuple):
    key, val = cigartuple
    color = CIGAR_EVENTS_COLOR_DD[key]
    make_line(ax, cx, cy, width=val, color=color)
    # val = cigartuple[1]
    # ax.text(x + val * 0.5, y - 0.01,
    #         f'del-{val}bp',
    #         va='top', ha='center', rotation=90)


def draw_ins(ax, cx, cy, cigartuple):
    key, val = cigartuple
    ax.scatter([cx + val / 2], [cy], marker='*', s=50)
#     pat = patches.Polygon([
#         [cx, cy],
#         [x - val / 2, y + 0.1],
#         [x + val / 2, y + 0.1]
#     ], facecolor='black', edgecolor='grey')
#     ax.add_patch(pat)
#     ax.text(x + span * 0.5, y + 0.03, f'In-{span}bp', va='bottom', ha='center', rotation=45)


def get_abs_start(aln):
    cx = aln.reference_start
    # bring to the absolute beginning
    for k, (key, val) in enumerate(aln.cigartuples):
        if k == 0 and key in [S.BAM_CSOFT_CLIP, S.BAM_CHARD_CLIP]:
            cx -= val
    return cx


def get_abs_end(aln):
    cx = aln.reference_end
    last_idx = len(aln.cigartuples) - 1
    # bring to the absolute beginning
    for k, (key, val) in enumerate(aln.cigartuples):
        if k == last_idx and key in [S.BAM_CSOFT_CLIP, S.BAM_CHARD_CLIP]:
            cx += val
    return cx


def calc_xlim(contig, nth_skip):
    """
    calculate the proper xlim boundries for the region between nth and nth+1 skip regions
    """
    assert nth_skip >= 0

    total_span = contig.reference_end - contig.reference_start
    skip_buffer = total_span * 0.002  # use this number to replace skip span
    # print(f'skip buffer: {int(skip_buffer)}')

    # init
    x0 = get_abs_start(contig) - 150
    x1 = get_abs_end(contig) + 150

    res = get_abs_start(contig)
    skip_count = 0
    for (key, val) in contig.cigartuples:
        if key == S.BAM_CREF_SKIP:
            skip_count += 1

        if key == S.BAM_CREF_SKIP:
            # print(skip_count, end=', ')
            if skip_count == nth_skip - 1:
                x0 = res + val - skip_buffer
            elif skip_count == nth_skip:
                x1 = res + skip_buffer
                break

        if key not in [S.BAM_CINS]:
            res += val
    return int(np.floor(x0)), int(np.ceil(x1))


def calc_xlim_pairs(contig):
    """calculate xlim pairs for each region in between two skip regions"""
    xlim_pairs = []
    num_skips = calc_num_skips(contig)
    for k in range(num_skips + 1):
        xlim = calc_xlim(contig, k + 1)
        xlim_pairs.append(xlim)

    df_xlims = pd.DataFrame(xlim_pairs, columns=['xmin', 'xmax'])
    df_xlims['span'] = df_xlims['xmax'] - df_xlims['xmin']
    return df_xlims
    # max_span = df_xlims.span.max()

    # out_xlim_pairs = []
    # for xl in xlim_pairs:
    #     spn = xl[1] - xl[0]
    #     pad = (max_span - spn) / 2
    # #     print(f'max_span spn, pad, xl[0], xl[1], {spn}, {max_span}, {pad}, {xl[0]}, {xl[1]}')
    #     nxmin, nxmax = xl[0] - pad, xl[1] + pad
    #     ax.text(0.6, 0.9, f'{int(np.floor(nxmin))} - {int(np.ceil(nxmax))}', transform=ax.transAxes)
    #     ax.set_xlim(nxmin, nxmax)


def calc_num_skips(contig):
    return len([_ for _ in contig.cigartuples if _[0] == S.BAM_CREF_SKIP])


def draw_alignment(ax, cx, cy, aln):
    """
    This function doesn't manipulate in anyway, it just draws CIGAR one after
    anther starting from cx, neigther does any of the element drawing functions

    contig follows duck typing with the needed attributes

    :param x: starting x
    :param y: starting y

    """
    dd = {
        S.BAM_CMATCH: draw_match,
        S.BAM_CSOFT_CLIP: draw_softclip,
        S.BAM_CHARD_CLIP: draw_hardclip,

        S.BAM_CREF_SKIP: draw_skip,
        S.BAM_CDEL: draw_del,

        S.BAM_CINS: draw_ins,
    }

    for k, cigartuple in enumerate(aln.cigartuples):
        key, val = cigartuple

        draw_func = dd[key]
        draw_func(ax, cx, cy, cigartuple)

        if key != S.BAM_CINS:
            cx += val


def convert_contig2genome_coord(target_ctg_pos, contig_aln):
    """
    :param ctg_pos: target position in contig coordinate
    """
    ref_pos = get_abs_start(contig_aln)
    ctg_pos = 0
    for k, (key, val) in enumerate(contig_aln.cigartuples):
        if key in [S.BAM_CSOFT_CLIP, S.BAM_CHARD_CLIP]:
            ctg_pos += val
            ref_pos += val
        elif key == S.BAM_CMATCH:
            ctg_pos += val
            ref_pos += val
        elif key == S.BAM_CREF_SKIP:
            ref_pos += val
        elif key == S.BAM_CDEL:
            ref_pos += val
        elif key == S.BAM_CINS:
            ctg_pos += val
        else:
            raise ValueError('unknown cigar key: {0}'.format(key))

        if ctg_pos >= target_ctg_pos:
            target_ref_pos = ref_pos - (ctg_pos - target_ctg_pos)
            return target_ref_pos
    raise ValueError('position is outside of the contig?')
