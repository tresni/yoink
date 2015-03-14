#!/usr/bin/env python

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

## DO NOT TOUCH THESE ##
user = ''
password = ''
target = ''
max_storage = ''
max_age = ''
storage_dir = ''
track_by_index_number = None
add_all_torrents_to_db = False

defaultrc = [
    "user:",
    "password:",
    "target:",
    "max_age:",
    "max_storage_in_mb:",
    "storage_dir:",
    "track_by_index_number:TRUE",
    "encoding:",
    "format:",
    "media:",
    "releasetype:"
]

headers = {
  'User-Agent': 'Yoink! Beta'
}


def printHelpMessage(header=''):
    if len(header) > 0:
        print header

    print """
Yoink! A Freeleech Torrent Grabber for What.CD
Developed by tobbez, forked by phracker and evanjd.
usage: python yoink.py [option]
Options:
--add-all-torrents-to-db : adds all existing freeleech torrents to the yoink
                           database without downloading the .torrent file.
                           Use this option if you want to ignore all
                           existing freeleech torrents and only yoink new ones.
--recreate-yoinkrc       : deletes existing ~/.yoinkrc and generates new file
                           with default settings. Use this if migrating from
                           another version of yoink.py
--help, -h -?            : this help message

Yoink settings are stored in ~/.yoinkrc. Accepted paramaters are:
   user:                  [your what.cd username]
   password:              [your what.cd password]
   target:                [your torrent client watch dir]
   max_age:               [the maximum age of a torrent in days that
                          yoink will download].
                          If left blank, will not check age of torrent.
   max_storage_in_mb:     [the maximum size in megabytes of your storage dir]
                          If the size of your storage folder exceeds the
                          specified size, yoink will stop downloading
                          new torrents.
                          Intended for seedboxes with limited storage quotas.
                          If left blank, will not check size of storage dir.
   storage_dir:           [your torrent data dir]
                          If left blank, defaults to home directory.
   track_by_index_number: [TRUE or FALSE]
                          if true, will write all downloaded torrent IDs to
                          ~/.yoink.db and use this as the primary mechanism
                          for checking if a given torrent has already
                          been yoinked.

Please see the wiki for filter options: http://git.io/5ZFi9A

NOTE: Parameters must be in the provided order!
"""


def isStorageFull(max_storage):
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
    if track_by_index_number:
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
    if track_by_index_number:
        if not torrentAlreadyDownloaded(tid):
            try:
                indexdb = sqlite3.connect(os.path.expanduser(dbpath))
                indexdbc = indexdb.cursor()
                indexdbc.execute("INSERT INTO snatchedtorrents values (?)", [tid])
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
    if not os.path.exists(target):
        print 'Target Directory does not exist, creating...'
        os.mkdir(target)

    if add_all_torrents_to_db:
        addTorrentToDB(tid)
        print 'Added {} to database.'.format(tid)
        return False

    if torrentAlreadyDownloaded(tid):
        print 'I have previously downloaded {}.'.format(tid)
        return False

    path = u''.join(os.path.join(target, name)).encode('utf-8').strip()
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


def main():
    rcpath = os.path.expanduser('~/.yoinkrc')

    if checkForArg('--help') or checkForArg('-h') or checkForArg('-?'):
        printHelpMessage()
        return 0

    if checkForArg('--recreate-yoinkrc'):
        if os.path.exists(rcpath):
            os.remove(rcpath)

    if not os.path.exists(rcpath):
        rcf = open(rcpath, 'w')
        rcf.write('\n'.join(defaultrc))
        rcf.flush()
        rcf.close()
        printHelpMessage('Wrote initial-run configuration file to ~/.yoinkrc\nYou will need to modify this file before continuing!\nSee below for accepted parameters:\n')
        return 0
    else:
        global user, password, target, max_age, max_storage, storage_dir, \
               track_by_index_number, format, media, releasetype
        with open(rcpath) as rcf:
            for line in rcf:
                key, value = line.split(':', 1)
                key = key.lower()
                if key == "user":
                    user = value
                elif key == "password":
                    password = value
                elif key == "target":
                    target = value
                elif key == "max_age":
                    max_age = value
                elif key == "max_storage":
                    max_storage = value
                elif key == "storage_dir":
                    storage_dir = value
                elif key == "track_by_index_number":
                    track_by_index_number = value
                elif key == "format":
                    format = value
                elif key == "media":
                    media = value
                elif key == "releasetype":
                    releasetype = value

        if not user or not password or not target or not track_by_index_number:
            printHelpMessage('ERROR: The ~/.yoinkrc configuration file appears incomplete!\nYou may need to use option --recreate-yoinkrc to revert your ~/.yoinkrc to the initial-run state for this version of Yoink.\n')
            return 0

        if max_age != '' and not max_age.isdigit():
            printHelpMessage('ERROR: Max Age (max_age) parameter must be a whole positive number.\n')
            return 0
        elif max_age == '':
            max_age = False
        else:
            max_age = int(max_age)

        if max_storage != '' and not max_storage.isdigit():
            printHelpMessage('ERROR: Max Storage (max_storage) parameter must be a whole positive number.\n')
            return 0
        elif max_storage == '':
            max_storage = False
        else:
            max_storage = int(max_storage)

        if storage_dir != '':
            try:
                storage_dir = os.path.expanduser(storage_dir)
                if not os.path.exists(storage_dir):
                    raise NameError('InvalidPath')
            except:
                printHelpMessage('ERROR: Storage directory (storage_dir) paramater does not resolve to a known directory.\n')
                return 0
        else:
            storage_dir = os.path.expanduser('~')

        if track_by_index_number.upper() == 'TRUE':
            track_by_index_number = True
            if not os.path.exists(os.path.expanduser(dbpath)):
                open(os.path.expanduser(dbpath), 'w+').close()
            indexdb = sqlite3.connect(os.path.expanduser(dbpath))
            indexdbc = indexdb.cursor()
            indexdbc.execute("CREATE TABLE IF NOT EXISTS snatchedtorrents (torrent_id NUMBER(100))")
            indexdb.commit()
        elif track_by_index_number.upper() == 'FALSE':
            track_by_index_number = False
        else:
            printHelpMessage('ERROR: Track by index number (track_by_index_number) parameter must be TRUE or FALSE.\n')
            return 0

        if checkForArg('--add-all-torrents-to-db'):
            global add_all_torrents_to_db
            add_all_torrents_to_db = True
            if not track_by_index_number:
                print 'WARNING: Adding all torrents to database with tracking by index number disabled will make this operation useless until you re-enable index number tracking.'

    search_params = 'search=&freetorrent=1' + '&encoding=' + encoding + '&format=' + format + '&media=' + media + '&releasetype=' + releasetype

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
        r = s.post('https://what.cd/login.php', data={'username': user, 'password': password, 'keeplogged': 1}, headers=headers)
        if r.url != u'https://what.cd/index.php':
            printHelpMessage("Login failed - come on, you're looking right at your password!\n")
            return

    with open(cookiefile, 'w') as f:
        pickle.dump(s.cookies, f)

    if max_age:
        cur_time = int(time.time())
        oldest_time = cur_time - (int(max_age) * (24 * 60 * 60))

    continueLeeching = True
    page = 1
    while continueLeeching:
        r = s.get('https://what.cd/torrents.php', params={
            'action': 'basic',
            'freetorrent': 1,
            'order_by': 'time',
            'order_way': 'desc',
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

            if max_age:
                date = r.xpath(".//span[contains(@class, 'time')]/@title")[0]
                date = time.mktime(time.strptime(date, "%b %d %Y, %H:%M"))
                if date < oldest_time and not add_all_torrents_to_db:
                    continueLeeching = False
                    break
            if isStorageFull(max_storage) and not add_all_torrents_to_db:
                continueLeeching = False
                print 'Your storage equals or exceeds ' + str(max_storage) + 'MB, exiting...'
                break
            if download_torrent(s, torrent_id, '{}.torrent'.format(torrent_id)):
                time.sleep(2)

        page += 1
        time.sleep(2)

    print '\n'
    print "Phew! All done."
    print '\n'
    print "Yoink!: The Freeleech Torrent Grabber for What.CD"
    print "\"Go Yoink! Yourself!\""

if __name__ == '__main__':
    main()
