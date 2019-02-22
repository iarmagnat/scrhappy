from datetime import datetime
import pickle
import sys
import sqlite3
from functools import wraps


from scrhappy.site import Site

def with_db(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        pik = pickle.dumps({"coucou": "coucou"}, pickle.HIGHEST_PROTOCOL)
        conn = sqlite3.connect("scrhappy_db")
        conn.execute('''CREATE TABLE IF NOT EXISTS 'sites' (
       'root' text NOT NULL,
       'pickle' blob NOT NULL,
       'dateLastScrapped' text NOT NULL);''')
        # conn.execute(
        #     ''' INSERT INTO sites(
        #     root,
        #     pickle,
        #     dateLastScrapped)
        #     VALUES ( ?, ?, ? ) ''',
        #     ("https://www.air-et-sante.fr", sqlite3.Binary(pik), datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))
        # )
        conn.commit()

        # call wrapped function
        func(conn)

        conn.close()

    return wrapper


def get_site(root, db, depth=30):
    site = False
    fetched = db.execute('''SELECT 
                root,
                pickle, 
                dateLastScrapped
                FROM sites WHERE root = '{}' '''.format(root)).fetchone()
    if fetched:
        age = datetime.now() - datetime.strptime(fetched[2], '%Y-%m-%d %H:%M:%S.%f')
        if age.days < 60:  # About 2 month
            site = pickle.loads(fetched[1])
            print("fetched from db")
    if not site:
        protocol, root_url = root.split("://")
        site = Site(root_url, protocol, depth=30)
        site.scrap_mono()

        pickled_site = pickle.dumps(site, pickle.HIGHEST_PROTOCOL)

        db.execute(
            ''' INSERT INTO sites(
            root,
            pickle,
            dateLastScrapped)
            VALUES ( ?, ?, ? ) ''',
            (root, sqlite3.Binary(pickled_site), datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))
        )
        db.commit()
        print("added into db")
    return site


@with_db
def main(db):
    root = sys.argv[1]

    site = get_site(root, db)

    print(site.get_links())


    # moi_mono = Site(root_url, protocol, depth=30)
    # print("done_scrapping: ", moi_mono.scrap_mono())
    # for e in moi_mono.entities:
    #     print(e)


if __name__ == '__main__':
    main()
