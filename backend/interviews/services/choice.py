''' Constrain final model decoding to a small explicit choice set. '''
import torch
from transformers import LogitsProcessor

class ChoiceLogitsProcessor(LogitsProcessor):
    ''' Restrict generation to token sequences representing allowed choices. '''
    def __init__(self, prompt_length, choice_token_ids, eos_token_id):
        ''' Store the prompt boundary and allowed token sequences. '''
        self.prompt_length = prompt_length
        self.choice_token_ids = choice_token_ids
        self.eos_token_id = eos_token_id

    def __call__(self, input_ids, scores):
        ''' Mask logits that cannot continue one of the allowed choices. '''
        generated = input_ids[0, self.prompt_length:].tolist()
        allowed = set()

        for choice in self.choice_token_ids:
            if generated == choice[:len(generated)]:
                if len(generated) < len(choice):
                    allowed.add(choice[len(generated)])
                else:
                    allowed.add(self.eos_token_id)

        mask = torch.full_like(scores, float('-inf'))

        for token_id in allowed:
            mask[:, token_id] = scores[:, token_id]

        return mask
