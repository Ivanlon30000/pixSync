import json
import logging
import sys
from typing import *

import yaml

from pix_sync import PixBookmarkSync


def get_logger(cfg) -> logging.Logger:
    logger = logging.Logger("pixSync")
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(logging.Formatter("[%(levelname)s]\t%(message)s"))
    logger.addHandler(log_handler)
    return logger


def load_token(token_path: str = "token.json") -> Dict[str, str]:
    with open(token_path, 'r', encoding="utf8") as fp:
        data = json.load(fp)
    return data


def load_config(config_path: str = "config.yaml") -> Dict[str, str]:
    with open(config_path, 'r', encoding="utf8") as fp:
        config = yaml.load(fp, Loader=yaml.Loader)
    return config


def main():
    config = load_config()
    token = load_token()
    
    logger = get_logger(config)
    logger.info(str(config))
    logger.info(str(token))
    
    pixSync = PixBookmarkSync(tokens=token, cfg=config, logger=logger)
    result = pixSync.sync()


if __name__ == "__main__":
    main()
