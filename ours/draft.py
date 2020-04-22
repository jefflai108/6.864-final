from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
import torch.nn.functional as F
import numpy as np


# Assume batch size = 1


MODEL = 'gpt2-medium'
DEV = 'cuda'
COND = 'negative politics'
COND = 'positive science'
COND = 'negative science'
TOP_K = 10
PREFIX = 'To conclude'
PREFIX = 'The potato'
LENGTH = 44
WEIGHT = 1


def top_k_filtering(logits, top_k=1, filter_value=-float("Inf"), min_tokens_to_keep=1):
    top_k = min(max(top_k, min_tokens_to_keep), logits.size(-1))
    ids_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
    ids_to_retain = torch.topk(logits, top_k)[1][0]
    logits[ids_to_remove] = filter_value
    return logits, ids_to_retain


def conditioning(logprobs, cond_ids, model, input_ids, ids_to_retain):
    input_ids = input_ids.repeat(TOP_K, 1)
    input_ids = torch.cat([input_ids, ids_to_retain.unsqueeze(1)], dim=-1)
    next_logits = model(input_ids)[0][:, -1]
    next_logprobs = F.log_softmax(next_logits, dim=-1)
    # cond_logprobs = torch.max(next_logprobs[:, cond_ids], dim=-1)[0]
    cond_logprobs = torch.mean(next_logprobs[:, cond_ids], dim=-1)
    logprobs[:, ids_to_retain] += WEIGHT * cond_logprobs
    probs = torch.exp(logprobs)
    return probs


tokenizer = GPT2Tokenizer.from_pretrained(MODEL)
model = GPT2LMHeadModel.from_pretrained(MODEL).to(DEV)
COND_IDS = tokenizer.encode(COND)

input_ids = torch.tensor([tokenizer.encode(PREFIX, add_special_tokens=True)]).to(DEV)

for t in range(LENGTH):
    with torch.no_grad():
        logits = model(input_ids)[0][:, -1]
        logits, ids_to_retain = top_k_filtering(logits, TOP_K)
        logprobs = F.log_softmax(logits, dim=-1)
        r = np.random.randint(0, int(1.5*len(COND_IDS)))
        if r >= len(COND_IDS):
            probs = torch.exp(logprobs)
        else:
            probs = conditioning(logprobs, [COND_IDS[r]], model, input_ids, ids_to_retain)
        next_tokens = torch.multinomial(probs, num_samples=1)
        input_ids = torch.cat([input_ids, next_tokens], dim=-1)

print(tokenizer.decode(input_ids[0]))