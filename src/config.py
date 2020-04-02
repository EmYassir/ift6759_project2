from typing_extensions import TypedDict


class ConfigEvalTransformer(TypedDict):
    debug: bool
    num_examples: int
    num_layers: int
    d_model: int
    dff: int
    num_heads: int
    dropout_rate: float
    checkpoint_path_best: str
    tokenizer_source_path: str
    tokenizer_target_path: str
    translation_batch_size: int


class ConfigTrainTransformer(TypedDict):
    num_examples: int
    num_layers: int
    d_model: int
    dff: int
    num_heads: int
    dropout_rate: float
    batch_size: int
    epochs: int
    source_unaligned: str
    source_training: str
    source_validation: str
    source_target_vocab_size: int
    target_unaligned: str
    target_training: str
    target_validation: str
    target_target_vocab_size: int
    checkpoint_path: str
    checkpoint_path_best: str
    tokenizer_source_path: str
    tokenizer_target_path: str