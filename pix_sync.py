import json
import logging
import os
import time
from typing import *

import pixivpy3 as pixiv
from tinydb import TinyDB, Query

from pathlib import Path
from BetterJSONStorage import BetterJSONStorage


class PixBookmarkSync:
    cfg: Dict[str, str]
    logger:logging.Logger
    api: pixiv.AppPixivAPI
    dbpath: TinyDB
    
    def __init__(self, tokens: Dict[str, str], cfg: Dict[str, str], logger: logging.Logger = None) -> None:
        self.cfg = cfg
        self.logger = logger if logger is not None else logging.getLogger()
        proxies = cfg.get('proxies', None)
        if proxies is not None:
            self.logger.info("Detect proxies: %s" % proxies)
        self.api = pixiv.AppPixivAPI(proxies=proxies, cookies={
            "PHPSESSID": tokens["sessid"]
        })
        
        # try to auth
        for i in range(self.cfg["max_retry"]):
            try:
                self.me = self.api.auth(refresh_token=tokens["refresh"])
            except Exception as e:
                logger.info(f"try to auth ({i+1}/{cfg['max_retry']})")
                time.sleep(1)
            else:
                break
        else:
            logger.error("auth failed, please retry")
            return
        logger.info("a new aapi has been initialized")
        
        # init database
        if "dbpath" in cfg:
            dbpath = cfg["dbpath"]
            self.dbpath = Path(dbpath)
            self.logger.info(f"load database {dbpath}")
        else:
            self.logger.warning("no database path(`dbpath`) set, download history will be lost")
            self.dbpath = None

    def get_downloaded_illusts(self) -> Set[int]:
        if self.dbpath is not None:
            with TinyDB(self.dbpath, access_mode="r+", storage=BetterJSONStorage) as db:
                illusts = db.all()
            return {int(illust["id"]) for illust in illusts}
        else:
            self.logger.warning("no download history, all bookmarks will be downloaded")
            return set()

    def download(self, illusts: List, save_dir: str) -> Dict[str, List]:
        result = {
            "success": [],
            "fail": []
        }
        for illust in illusts:
            try:
                if illust["type"] in {"illust", "manga"}:
                    if illust["page_count"] == 1:
                        self.api.download(illust["meta_single_page"]["original_image_url"], 
                                          path=save_dir)
                    else:
                        for url in illust["meta_pages"]:
                            url = url["image_urls"]["original"]
                            self.api.download(url, path=save_dir)
                    self.logger.info(f"{illust['id']} downloaded at {save_dir}")
                elif illust["type"] == "ugoira":
                    # TODO
                    self.logger.warning(f"not support ugoira, id {illust['id']}")
                    raise ValueError("unsupport ugoira")
            except Exception as e:
                result["fail"].append((illust["id"], str(e)))
            else:
                result["success"].append(illust)
            finally:
                if self.dbpath is not None:
                    with TinyDB(self.dbpath, access_mode="r+", storage=BetterJSONStorage) as db:
                        db.insert_multiple(result["success"])
                
        return result

    def sync(self) -> Dict[str, List]:
        illusts = []
        for restrict in self.cfg["restrict"]:
            mbi = None
            while True:
                res = self.api.user_bookmarks_illust(
                    self.me["user"]["id"], restrict=restrict, max_bookmark_id=mbi)
                illusts.extend(res["illusts"])
                self.logger.info(f"get {len(illusts)} illusts")
                if res["next_url"]:
                    mbi = self.api.parse_qs(res["next_url"])["max_bookmark_id"]
                    time.sleep(0.5)
                else:
                    break
        self.logger.info(f"you now have {len(illusts)} bookmarked illusts.")
        
        downloaded_illusts = self.get_downloaded_illusts()
        new_illusts = [illust for illust in illusts if int(illust["id"]) not in downloaded_illusts]
        self.logger.info(f"where there are {len(new_illusts)} new illusts")
        
        self.logger.info("start downloading")
        os.makedirs(self.cfg["savepath"], exist_ok=True)
        result = self.download(new_illusts, self.cfg["savepath"])
        self.logger.info(f"finish: {len(result['success'])} success, {len(result['fail'])} fail:")
        if result["fail"]:
            self.logger.info('\n'.join([f"\t{id} - {exc}" for id, exc in result['fail']]))

        return result


if __name__ == "__main__":
    pass
