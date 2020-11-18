"""
Downloads the GPT-2 model for use in bot replies. Used in a build step to provide the model.
"""
from gpt2_client import GPT2Client

if __name__ == '__main__':
    gpt2 = GPT2Client('117M')  # This could also be `345M`, `774M`, or `1558M`. Rename `save_dir` to anything.
    gpt2.load_model(force_download=True)
