"""
Utility functions for Transformer model
"""

from typing import Tuple

import matplotlib.pyplot as plt
import tensorflow as tf
import tensorflow_datasets as tfds

from src.models.Transformer import Transformer


class CustomSchedule(tf.keras.optimizers.schedules.LearningRateSchedule):
    """
    Creates custom learning rate scheduler for Transformer
    """
    def __init__(self, d_model, warmup_steps=4000):
        super(CustomSchedule, self).__init__()

        self.d_model = d_model
        self.d_model = tf.cast(self.d_model, tf.float32)

        self.warmup_steps = warmup_steps

    def __call__(self, step):
        arg1 = tf.math.rsqrt(step)
        arg2 = step * (self.warmup_steps ** -1.5)

        return tf.math.rsqrt(self.d_model) * tf.math.minimum(arg1, arg2)


def create_padding_mask(seq):
    """
    Create mask to use padding provided by input sequence
    :param seq: Input sequence
    :return: Mask that masks elements where input sequence is 0
    """
    seq = tf.cast(tf.math.equal(seq, 0), tf.float32)

    # add extra dimensions to add the padding
    # to the attention logits.
    return seq[:, tf.newaxis, tf.newaxis, :]  # (batch_size, 1, 1, seq_len)


def create_look_ahead_mask(size):
    """
    Create mask to prevent looking at future elements in decoder
    :param size: size of sequence
    :return: Mask that masks future elements in decoder input sequence
    """
    mask = 1 - tf.linalg.band_part(tf.ones((size, size)), -1, 0)
    return mask  # (seq_len, seq_len)


def create_masks(inp, tar):
    """
    Create masks for transformer
    :param inp: input sequence
    :param tar: target sequence
    :return: encoder padding mask, combined_mask and decoder padding mask
    """
    # Encoder padding mask
    enc_padding_mask = create_padding_mask(inp)

    # Used in the 2nd attention block in the decoder.
    # This padding mask is used to mask the encoder outputs.
    dec_padding_mask = create_padding_mask(inp)

    # Used in the 1st attention block in the decoder.
    # It is used to pad and mask future tokens in the input received by
    # the decoder.
    look_ahead_mask = create_look_ahead_mask(tf.shape(tar)[1])
    dec_target_padding_mask = create_padding_mask(tar)
    combined_mask = tf.maximum(dec_target_padding_mask, look_ahead_mask)

    return enc_padding_mask, combined_mask, dec_padding_mask


def evaluate(inp_sentence: str, tokenizer_source: tfds.features.text.SubwordTextEncoder,
             tokenizer_target: tfds.features.text.SubwordTextEncoder, max_length_pred: int,
             transformer: Transformer) -> Tuple:
    """
    Takes an input sentence and generate the sequence of tokens for its translation
    :param inp_sentence: Input sentence in source language
    :param tokenizer_source: Tokenizer for source language
    :param tokenizer_target: Tokenizer for target language
    :param max_length_pred: Maximum length of output sequence
    :param transformer: Trained Transformer model
    :return: The sequence of token ids in target language, the attention weights
    """
    start_token = [tokenizer_source.vocab_size]
    end_token = [tokenizer_source.vocab_size + 1]

    # Adding the start and end token to input
    inp_sentence = start_token + tokenizer_source.encode(inp_sentence) + end_token
    encoder_input = tf.expand_dims(inp_sentence, 0)

    # The first word to the transformer should be the target start token
    decoder_input = [tokenizer_target.vocab_size]
    output = tf.expand_dims(decoder_input, 0)

    for i in range(max_length_pred):
        enc_padding_mask, combined_mask, dec_padding_mask = create_masks(encoder_input, output)

        # predictions.shape == (batch_size, seq_len, vocab_size)
        predictions, attention_weights = transformer(encoder_input,
                                                     output,
                                                     False,
                                                     enc_padding_mask,
                                                     combined_mask,
                                                     dec_padding_mask)

        # select the last word from the seq_len dimension
        predictions = predictions[:, -1:, :]  # (batch_size, 1, vocab_size)

        predicted_id = tf.cast(tf.argmax(predictions, axis=-1), tf.int32)

        # return the result if the predicted_id is equal to the end token
        if predicted_id == tokenizer_target.vocab_size + 1:
            return tf.squeeze(output, axis=0), attention_weights

        # concatenate the predicted_id to the output which is given to the decoder as its input.
        output = tf.concat([output, predicted_id], axis=-1)

    return tf.squeeze(output, axis=0), attention_weights


def plot_attention_weights(attention, sentence, result, layer, tokenizer_source, tokenizer_target):
    """
    Plot attention weights for a given layer
    :param attention: Attention weights
    :param sentence: Tokenized input sentence
    :param result: Tokenized translated sentence
    :param layer: Name of layer to plot ex('decoder_layer4_block2')
    :param tokenizer_source: Source language tokenizer
    :param tokenizer_target: Target language tokenizer
    """
    fig = plt.figure(figsize=(16, 8))

    sentence = tokenizer_source.encode(sentence)

    attention = tf.squeeze(attention[layer], axis=0)

    for head in range(attention.shape[0]):
        ax = fig.add_subplot(2, 4, head + 1)

        # plot the attention weights
        ax.matshow(attention[head][:-1, :], cmap='viridis')

        fontdict = {'fontsize': 10}

        ax.set_xticks(range(len(sentence) + 2))
        ax.set_yticks(range(len(result)))

        ax.set_ylim(len(result) - 1.5, -0.5)

        ax.set_xticklabels(
            ['<start>'] + [tokenizer_source.decode([i]) for i in sentence] + ['<end>'],
            fontdict=fontdict, rotation=90)

        ax.set_yticklabels([tokenizer_target.decode([i]) for i in result
                            if i < tokenizer_target.vocab_size],
                           fontdict=fontdict)

        ax.set_xlabel('Head {}'.format(head + 1))

    plt.tight_layout()
    plt.show()


def translate(inp_sentence: str, tokenizer_source: tfds.features.text.SubwordTextEncoder,
              tokenizer_target: tfds.features.text.SubwordTextEncoder, max_length_pred: int,
              transformer: Transformer, plot: str = "") -> str:
    """
    Translate a sentence from source to target language
    :param inp_sentence: input sentence in source language
    :param tokenizer_source: tokenizer for source language
    :param tokenizer_target: tokenizer for target language
    :param max_length_pred: maximum number of tokens in output sentence
    :param transformer: Trained Transformer model
    :param plot: Name of layer to plot (will not plot if "")
    :return: The translated sentence in target language
    """
    result, attention_weights = evaluate(inp_sentence, tokenizer_source, tokenizer_target, max_length_pred, transformer)

    predicted_sentence = tokenizer_target.decode([i for i in result if i < tokenizer_target.vocab_size])
    if plot:
        plot_attention_weights(attention_weights, inp_sentence, result, plot, tokenizer_source, tokenizer_target)
    return predicted_sentence
