"""
Downloads the GPT-2 model for use in bot replies. Used in a build step to provide the model.
"""
import os

import gpt_2_simple as gpt2

model_name = "124M"

if __name__ == '__main__':
    if not os.path.isdir(os.path.join("models", model_name)):
        print(f"Downloading {model_name} model...")
        gpt2.download_gpt2(model_name=model_name)  # model is saved into current directory under /models/124M/
