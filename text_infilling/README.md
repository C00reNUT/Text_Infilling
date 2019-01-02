# Texar Examples #

Rich examples are included to demonstrate the use of Texar. The implementations of cutting-edge models/algorithms also provide references for reproducibility and comparisons. 

More examples are continuously added...

## Examples by Models/Algorithms ##

### RNN / Seq2seq ###

* [language_model_ptb](./language_model_ptb): Basic RNN language model
* [seq2seq_attn](./seq2seq_attn): Attentional seq2seq
* [seq2seq_configs](./seq2seq_configs): Seq2seq implemented with Texar model template.
* [seq2seq_rl](./seq2seq_rl): Attentional seq2seq trained with policy gradient.
* [hierarchical_dialog](./hierarchical_dialog): Hierarchical recurrent encoder-decoder model for conversation response generation.
* [torchtext](./torchtext): Use of torchtext data loader

### Transformer (Self-attention) ###

* [transformer](./transformer): Transformer for machine translation
* [vae_text](./vae_text): VAE with a transformer decoder for improved language modeling 

### Variational Autoencoder (VAE) ###

* [vae_text](./vae_text): VAE language model

### GANs / Discriminiator-supervision ###

* [seqGAN](./seqgan): GANs for text generation
* [text_style_transfer](./text_style_transfer): Discriminator supervision for controlled text generation

### Reinforcement Learning ###

* [seq2seq_rl](./seq2seq_rl): Attentional seq2seq trained with policy gradient.
* [seqGAN](./seqgan): Policy gradient for sequence generation
* [rl_gym](./rl_gym): Various RL algoritms for games

### Memory Network ###

* [memory_network_lm](./memory_network_lm): End-to-end memory network for language modeling

### Classifier / Predictions ##  

* [sentence_classifier](./sentence_classifier): Basic CNN-based sentence classifier

---

## Examples by Tasks

### Language Modeling ###

* [language_model_ptb](./language_model_ptb)
* [vae_text](./vae_text)
* [seqGAN](./seqgan)
* [memory_network_lm](./memory_network_lm)

### Machine Translation ###

* [seq2seq_attn](./seq2seq_attn)
* [seq2seq_configs](./seq2seq_configs)
* [seq2seq_rl](./seq2seq_rl)
* [transformer](./transformer)

### Dialog ###

* [hierarchical_dialog](./hierarchical_dialog)

### Text Style Transfer ###

* [text_style_transfer](./text_style_transfer)

### Classification ###

* [sentence_classifier](./sentence_classifier)

### Games ###

* [rl_gym](./rl_gym)