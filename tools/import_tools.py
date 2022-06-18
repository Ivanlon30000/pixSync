import json
from tqdm import tqdm
from tinydb import TinyDB
import argparse
from BetterJSONStorage import BetterJSONStorage
from pathlib import Path

def import_from(jsonfile:str, dbfile:str):
    with open(jsonfile, 'r', encoding="utf8") as fp:
        data = json.load(fp)
    data = [illust for illust in data if "id" in illust]
    
    dbfile = Path(dbfile)
    # if not dbfile.exists():
    #     with open(dbfile, "w"):
    #         pass
    
    with TinyDB(dbfile, access_mode="r+", storage=BetterJSONStorage) as db:
        exists_illusts = {illust["id"] for illust in db.all()} 
        for illust in tqdm(data):
            if illust["id"] not in exists_illusts:
                db.insert(illust)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--json", required=True, help="json file")
    parser.add_argument("-d", "--dbfile", required=True, help="database file")
    args = parser.parse_args()
    print(f"import download history from {args.json} to {args.dbfile}")
    import_from(args.json, args.dbfile)
    print("import done.")