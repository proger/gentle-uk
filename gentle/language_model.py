import math
from pathlib import Path
import subprocess
import sys


from .util.paths import get_binary, hash_string
from .metasentence import MetaSentence
from .resources import Resources

MKGRAPH_PATH = get_binary("ext/m3")

# [oov] no longer in words.txt
OOV_TERM = '<unk>'

def make_bigram_lm_fst(word_sequences, **kwargs):
    '''
    Use the given token sequence to make a bigram language model
    in OpenFST plain text format.

    When the "conservative" flag is set, an [oov] is interleaved
    between successive words.

    When the "disfluency" flag is set, a small set of disfluencies is
    interleaved between successive words

    `Word sequence` is a list of lists, each valid as a start
    '''

    if len(word_sequences) == 0 or type(word_sequences[0]) != list:
        word_sequences = [word_sequences]

    conservative = kwargs['conservative'] if 'conservative' in kwargs else False
    disfluency = kwargs['disfluency'] if 'disfluency' in kwargs else False
    disfluencies = kwargs['disfluencies'] if 'disfluencies' in kwargs else []

    # yolo
    disfluency = True
    disfluencies = [OOV_TERM]

    bigrams = {OOV_TERM: set([OOV_TERM])}
    
    for word_sequence in word_sequences:
        if len(word_sequence) == 0:
            continue

        prev_word = word_sequence[0]
        bigrams[OOV_TERM].add(prev_word) # valid start (?)

        if disfluency:
            bigrams[OOV_TERM].update(disfluencies)

            for dis in disfluencies:
                bigrams.setdefault(dis, set()).add(prev_word)
                bigrams[dis].add(OOV_TERM)

        for word in word_sequence[1:]:
            bigrams.setdefault(prev_word, set()).add(word)

            if conservative:
                bigrams[prev_word].add(OOV_TERM)

            if disfluency:
                bigrams[prev_word].update(disfluencies)

                for dis in disfluencies:
                    bigrams[dis].add(word)

            prev_word = word

        # ...valid end
        bigrams.setdefault(prev_word, set()).add(OOV_TERM)

    node_ids = {}
    def get_node_id(word):
        node_id = node_ids.get(word, len(node_ids) + 1)
        node_ids[word] = node_id
        return node_id

    output = ""
    for from_word in sorted(bigrams.keys()):
        from_id = get_node_id(from_word)

        successors = bigrams[from_word]
        if len(successors) > 0:
            weight = -math.log(1.0 / len(successors))
        else:
            weight = 0

        for to_word in sorted(successors):
            to_id = get_node_id(to_word)
            output += '%d    %d    %s    %s    %f' % (from_id, to_id, to_word, to_word, weight)
            output += "\n"

    output += "%d    0\n" % (len(node_ids))

    return output

def make_bigram_language_model(kaldi_seq, exp, **kwargs):
    """Generates a language model to fit the text.

    Returns the filename of the generated language model FST.
    The caller is resposible for removing the generated file.

    `exp` is a path to a directory containing prototype model data
    `kaldi_seq` is a list of words within kaldi's vocabulary.
    """

    graph = exp / 'graph' / hash_string(*kaldi_seq)
    graph.mkdir(parents=True, exist_ok=True)

    # Generate a textual FST
    txt_fst = make_bigram_lm_fst(kaldi_seq, **kwargs)
    txt_fst_file = graph / 'lm.txt'
    txt_fst_file.write_text(txt_fst)

    hclg_filename = graph / 'HCLG.fst'
    subprocess.check_output([MKGRAPH_PATH, exp, txt_fst_file, hclg_filename])

    return hclg_filename

if __name__=='__main__':
    import sys
    make_bigram_language_model(open(sys.argv[1]).read(), Path(Resources().proto_langdir))
