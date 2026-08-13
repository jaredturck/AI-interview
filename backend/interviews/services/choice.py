''' Guarantee machine-readable model decisions by restricting decoding to explicit application choices. '''
import torch
from transformers import LogitsProcessor

class ChoiceLogitsProcessor(LogitsProcessor):
    ''' Force generation to remain on token paths that can complete one approved choice. '''
    def __init__(self, prompt_length, choice_token_ids, eos_token_id):
        ''' Define the prompt boundary and valid token paths used to constrain model decoding. '''
        self.prompt_length = prompt_length
        self.choice_token_ids = choice_token_ids
        self.eos_token_id = eos_token_id

    def __call__(self, input_ids, scores):
        ''' Allow only next tokens that can still complete an approved choice. '''
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
