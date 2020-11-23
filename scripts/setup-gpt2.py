"""
Downloads the GPT-2 model for use in bot replies. Used in a build step to provide the model.
"""
from transformers import AutoTokenizer, AutoModelWithLMHead

if __name__ == '__main__':
    tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium", cache_dir='models')
    model = AutoModelWithLMHead.from_pretrained("microsoft/DialoGPT-medium", cache_dir='models')
