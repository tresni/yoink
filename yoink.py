#!/usr/bin/env python

import argparse
import time
import cPickle as pickle
import json
import requests
import html5lib
import os
import re
import sys
import sqlite3

## SAFE TO EDIT ##
dbpath = '~/.yoink.db'

defaultrc = [
    "user:",
    "password:",
    "target:",
    "max_age:1",
    "#max_storage_in_mb:",
    "#storage_dir:",
    "track_by_index_number:TRUE",
    "#encoding:",
    "#format:",
    "#media:",
    "#releasetype:"
]

headers = {
  'User-Agent': 'Yoink! Beta'
}

# TODO: Remove this when we get rid of the global below
args = {}


def isStorageFull(max_storage, storage_dir):
    if not max_storage:
        return False

    totalSize = sum(os.path.getsize(u''.join(os.path.join(dirpath, filename))
                                       .encode('utf-8').strip())
                    for dirpath, dirnames, filenames in os.walk(storage_dir)
                    for filename in filenames) / 1024 / 1024
    if totalSize >= max_storage:
        return True
    else:
        return False


def torrentAlreadyDownloaded(tid):
    if args.track_by_index_number:
        try:
            indexdb = sqlite3.connect(os.path.expanduser(dbpath))
            indexdbc = indexdb.cursor()
            indexdbc.execute("SELECT COUNT(*) FROM snatchedtorrents WHERE torrent_id = (?)", [tid])
            if int(str(indexdbc.fetchone())[1]) == 0:
                torrent_found = False
            else:
                torrent_found = True
        except Exception as e:
            print 'Error when executing SELECT on ~/.yoink.db:'
            print str(e)
            sys.exit()
        finally:
            if indexdb:
                indexdbc.close()
            return torrent_found
    else:
        return False


def addTorrentToDB(tid):
    if args.track_by_index_number:
        try:
            indexdb = sqlite3.connect(os.path.expanduser(dbpath))
            indexdbc = indexdb.cursor()
            indexdbc.execute("INSERT OR REPLACE INTO snatchedtorrents values (?)", [tid])
            indexdb.commit()
        except Exception as e:
            print 'Error when executing INSERT on ~/.yoink.db:'
            print str(e)
            sys.exit()
        finally:
            if indexdb:
                indexdbc.close()


def checkForArg(arg):
    for clarg in sys.argv[1:]:
        if arg.lower() == clarg.lower():
            return True
    return False


def download_torrent(session, tid, name):
    if not os.path.exists(args.target):
        print 'Target Directory does not exist, creating...'
        os.mkdir(args.target)

    if args.add_all_torrents_to_db:
        addTorrentToDB(tid)
        print 'Added {} to database.'.format(tid)
        return False

    if torrentAlreadyDownloaded(tid):
        print 'I have previously downloaded {}.'.format(tid)
        return False

    path = u''.join(os.path.join(args.target, name)).encode('utf-8').strip()
    if os.path.exists(path):
        print 'I already haz {}.'.format(tid)
        addTorrentToDB(tid)
        return False

    if not hasattr(download_torrent, 'authdata'):
        r = session.get('https://what.cd/ajax.php?action=index', headers=headers)
        d = json.loads(r.content)
        download_torrent.authdata = '&authkey={}&torrent_pass={}'.format(d['response']['authkey'], d['response']['passkey'])

    print '{}:'.format(tid),
    dl = session.get('https://what.cd/torrents.php?action=download&id={}{}'.format(tid, download_torrent.authdata), headers=headers)
    with open(path, 'wb') as f:
        for chunk in dl.iter_content(1024*1024):
            f.write(chunk)
    addTorrentToDB(tid)
    print 'Yoink!'

    return True

class CustomArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(CustomArgumentParser, self).__init__(*args, **kwargs)

    def convert_arg_line_to_args(self, line):
        if line[0] == "#":
            return
        key, value = line.split(':', 1)
        if value:
            yield "--%s=%s" % (key, value)
        else:
            yield "--%s" % key


def main():
    # TODO: Remove this and make this stuff work better...
    global args
    rcpath = os.path.expanduser('~/.yoinkrc')

    def positive_number(string):
        value = int(string)
        if value >= 0:
            return value
        else:
            raise argparse.ArgumentTypeError("%r is not >= 0" % string)

    def path_exists(string):
        if os.path.exists(os.path.expanduser(string)):
            return os.path.expanduser(string)
        else:
            raise argparse.ArgumentTypeError("%r does not exist" % string)

    parser = CustomArgumentParser(fromfile_prefix_chars="@")
    parser.add_argument("--user", type=str, required=True,
                        help="what.cd username")
    parser.add_argument("--password", type=str, required=True,
                        help="what.cd password")
    parser.add_argument("--target", type=path_exists, required=True,
                        help="target directory")
    parser.add_argument("--max_age", type=positive_number, default=3,
                        help="Max age of torrent in days")
    parser.add_argument("--max_storage_in_mb", type=positive_number, default=0,
                        dest="max_storage",
                        help="Max disk space used by storage directory")
    parser.add_argument("--storage_dir", type=path_exists, default="~",
                        help="Where torrent data is stored")
    parser.add_argument("--track_by_index_number", type=bool, default=True,
                        help="Track index numbers")
    parser.add_argument("--encoding", type=str,
                        help="Encoding to download")
    parser.add_argument("--format", type=str,
                        help="Formats to download")
    parser.add_argument("--media", type=str,
                        help="Media to download")
    parser.add_argument("--releasetype", type=str,
                        help="Release type to download")
    parser.add_argument("--recreate-yoinkrc", action="store_true",
                        help="Recreate initial .yoinkrc")
    parser.add_argument("--add-all-torrents-to-db", "-a",
                        action="store_true",
                        help="Add all parsed torrents to the database.  Good "
                             "for the inital run.")

    if os.path.exists(rcpath):
        args = ["@%s" % rcpath] + sys.argv[1:]
    else:
        args = sys.argv[1:]

    args = parser.parse_args(args)

    if args.recreate_yoinkrc:
        if os.path.exists(rcpath):
            os.remove(rcpath)
        with open(rcpath, "w") as fp:
            fp.write("\n".join(defaultrc))

    if args.track_by_index_number:
        if not os.path.exists(os.path.expanduser(dbpath)):
            open(os.path.expanduser(dbpath), 'w+').close()
        indexdb = sqlite3.connect(os.path.expanduser(dbpath))
        indexdbc = indexdb.cursor()
        indexdbc.execute("CREATE TABLE IF NOT EXISTS snatchedtorrents (torrent_id NUMBER(100))")
        indexdb.commit()

    if args.add_all_torrents_to_db and not args.track_by_index_number:
        print 'WARNING: Adding all torrents to database with tracking by index number disabled will make this operation useless until you re-enable index number tracking.'

    s = requests.session()

    cookiefile = os.path.expanduser('~/.yoink.dat')
    if os.path.exists(cookiefile):
        with open(cookiefile, 'r') as f:
            s.cookies = pickle.load(f)

    connected = False
    connectionAttempts = 0

    while not connected and connectionAttempts < 10:
        try:
            connectionAttempts += 1
            r = s.get('https://what.cd/login.php')
            connected = True
        except requests.exceptions.TooManyRedirects:
            s.cookies.clear()
        except requests.exceptions.RequestException as e:
            print e
            sys.exit(1)

    if r.url != u'https://what.cd/index.php':
        r = s.post('https://what.cd/login.php',
                   data={'username': args.user,
                         'password': args.password,
                         'keeplogged': 1},
                   headers=headers)
        if r.url != u'https://what.cd/index.php':
            print "Login failed - come on, you're looking right at your password!"
            return

    with open(cookiefile, 'w') as f:
        pickle.dump(s.cookies, f)

    if args.max_age:
        cur_time = int(time.time())
        oldest_time = cur_time - (args.max_age * (24 * 60 * 60))

    continueLeeching = True
    page = 1
    while continueLeeching:
        r = s.get('https://what.cd/torrents.php', params={
            'action': 'basic',
            'freetorrent': 1,
            'order_by': 'time',
            'order_way': 'desc',
            'encoding': args.encoding,
            'format': args.format,
            'media': args.media,
            'releasetype': args.releasetype,
            'page': page
        }, headers=headers)

        if r.status_code != 200:
            print r.status_code
            print r.text

        document = html5lib.parse(r.text, treebuilder="lxml", namespaceHTMLElements=False)
        results = document.xpath("//tr[contains(@class, 'torrent')]")

        if not results:
            print "No more torrents"
            break

        for r in results:
            download = r.xpath(".//a[@title='Download']/@href")[0]
            torrent_id = re.search('id=(\d+)', download).group(1)

            if args.max_age:
                date = r.xpath(".//span[contains(@class, 'time')]/@title")[0]
                date = time.mktime(time.strptime(date, "%b %d %Y, %H:%M"))
                if date < oldest_time and not args.add_all_torrents_to_db:
                    continueLeeching = False
                    break
            if isStorageFull(args.max_storage, args.storage_dir) and not args.add_all_torrents_to_db:
                continueLeeching = False
                print 'Your storage equals or exceeds ' + str(args.max_storage) + 'MB, exiting...'
                break
            if download_torrent(s, torrent_id, '{}.torrent'.format(torrent_id)):
                time.sleep(2)

        page += 1
        time.sleep(2)

    print """
Phew! All done.

Yoink!: The Freeleech Torrent Grabber for What.CD
\"Go Yoink! Yourself!\"
"""

if __name__ == '__main__':
    main()
