import os
import yaml

CONFIG_FILE = os.path.expanduser('~/.git-wise.yaml')

#  sadly, I can't pay my openai bill. so this cant provide to you. T T
AUTHOR_API_KEY = "nothing"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)

# I dont know why aws cli also save the api key in the config file https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-where
# I will change this if have time
def get_api_key(use_author_key=False):
    # if use_author_key:
    if False:
        return AUTHOR_API_KEY
    config = load_config()
    return config.get('openai_api_key') or os.environ.get('OPENAI_API_KEY')
