import json
import logging
import os
import pickle
import sys
import time
from typing import *

import pixivpy3 as pixiv
import yaml

logger = logging.Logger("pixSync", level=logging.DEBUG)
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.DEBUG)
log_handler.setFormatter(logging.Formatter("[%(levelname)s]\t%(message)s"))
logger.addHandler(log_handler)


def load_token(token_path: str = "token.json") -> Dict[str, str]:
    with open(token_path, 'r', encoding="utf8") as fp:
        data = json.load(fp)
    return data


def load_config(config_path: str = "config.yaml") -> Dict[str, str]:
    with open(config_path, 'r', encoding="utf8") as fp:
        config = yaml.load(fp, Loader=yaml.Loader)
    return config


def get_downloaded_illusts(metapath: str = "bookmark.json") -> Set[int]:
    try:
        with open(metapath, 'r', encoding="utf8") as fp:
            data = json.load(fp)
    except FileNotFoundError:
        return set()
    else:
        return set([int(illust["id"]) for illust in data])


def download(api: pixiv.AppPixivAPI, illusts: List, save_dir: str) -> Dict:
    result = {
        "success": [],
        "fail": []
    }
    for illust in illusts:
        try:
            if illust["type"] in {"illust", "manga"}:
                if illust["page_count"] == 1:
                    api.download(illust["meta_single_page"]
                                 ["original_image_url"], path=save_dir)
                else:
                    for url in illust["meta_pages"]:
                        url = url["image_urls"]["original"]
                        api.download(url, path=save_dir)
                logger.info(f"{illust['id']} downloaded at {save_dir}")
                result["success"].append(illust["id"])
            elif illust["type"] == "ugoira":
                # TODO
                logger.warning(f"not support ugoira, id {illust['id']}")
                result["fail"].append(illust["id"])
        except Exception as e:
            result["fail"].append((illust["id"], str(e)))
    return result


def main():
    config = load_config()
    token = load_token()
    logger.info(str(config))
    logger.info(str(token))

    api = pixiv.AppPixivAPI(cookies={
        "PHPSESSID": token["sessid"]
    })
    logger.info("init new aapi")

    for i in range(config["max_retry"]):
        try:
            me = api.auth(refresh_token=token["refresh"])
        except Exception as e:
            logger.info(f"try to auth ({i+1}/{config['max_retry']})")
            time.sleep(1)
        else:
            break
    else:
        logger.error("auth failed, please retry")
        exit(255)

    illusts = []
    for restrict in config["restrict"]:
        mbi = None
        while True:
            res = api.user_bookmarks_illust(
                me["user"]["id"], restrict=restrict, max_bookmark_id=mbi)
            illusts.extend(res["illusts"])
            logger.info(f"get {len(illusts)} illusts")
            if res["next_url"]:
                mbi = api.parse_qs(res["next_url"])["max_bookmark_id"]
                time.sleep(0.5)
            else:
                break

    downloaded_illusts = get_downloaded_illusts()
    new_illusts = [illust for illust in illusts if int(
        illust["id"]) not in downloaded_illusts]
    logger.info(f"{len(new_illusts)} new illusts")

    os.makedirs(config["save_path"], exist_ok=True)
    result = download(api, new_illusts, config["save_path"])
    logger.info(
        f"finish: {len(result['success'])} success, {len(result['fail'])} fail:")
    if result["fail"]:
        logger.info('\n'.join([f"{id} - {exc}" for id, exc in result['fail']]))


if __name__ == "__main__":
    api = main()
