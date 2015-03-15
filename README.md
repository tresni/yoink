<p align="center">
<img src="https://i.imgur.com/C8OW3yw.png" alt="Yoink">
</p>

*A Freeleech Torrent Grabber for What.CD*
===

Requires python2.7 + pip + `$ pip install requests html5lib lxml`

Usage: `python yoink.py [option]`

For a full list of options, execute `python yoink.py -h`

Options:

```
-h, --help            show this help message and exit
--user USER, -u USER  your what.cd username
--password PASSWORD, -p PASSWORD
                      your what.cd password
--target TARGET, -t TARGET
                      your torrent client watch directory
--max_age MAX_AGE, -o MAX_AGE
                      the maximum age of a torrent in days that yoink will
                      download. If set to 0, yoink will not check the age of
                      the torrent.
--max_storage_in_mb MAX_STORAGE, -b MAX_STORAGE
                      the maximum size in megabytes of your storage
                      directory. If the size of your storage directory
                      exceeds the specified size, yoink will stop
                      downloading new torrents. This runs on the assumption
                      that your torrent client preallocated the space
                      required for each torrent immediately after the
                      .torrent folder is added to your watch directory. If
                      set to 0, the default, yoink will not check the size
                      of your storage area. This is intended for seedboxes
                      with limited storage quotas.
--storage_dir STORAGE_DIR, -s STORAGE_DIR
                      your torrent data directory. Defaults to your home
                      directory
--track_by_index_number TRACK_BY_INDEX_NUMBER, -i TRACK_BY_INDEX_NUMBER
                      write all downloaded torrent IDs to ~/.yoink.db and
                      use this as the primary mechanism for checking if a
                      given torrent has already been yoinked.
--encoding ENCODING, -e ENCODING
                      Encoding to download
--format FORMAT, -f FORMAT
                      Formats to download
--media MEDIA, -m MEDIA
                      Media to download
--releasetype RELEASETYPE, -r RELEASETYPE
                      Release type to download
--recreate-yoinkrc    deletes existing ~/.yoinkrc and generates new file
                      with default settings. Use this if migrating from
                      another version of yoink.py
--add-all-torrents-to-db, -a
                      adds all existing freeleech torrents to the yoink
                      database without downloading the .torrent file. Use
                      this option if you want to ignore all existing
                      freeleech torrents and only yoink new ones.
```

Yoink settings can be stored in ~/.yoinkrc. Accepted parameters are the same as the command line, formated as `key:value` pairs, one per line.  Comments can be included by starting the line with `#`.

Example .yoinkrc
---
```
user:john.smith@hotmail.com
password:MyPasswordIsSecure!
target:~/torrents
```


[Filter Configuration Information](http://git.io/5ZFi9A)

To create a cron job that executes this script every hour, simply:

`$ crontab -e`

and add:

`00 * * * * python /path/to/yoink.py`

*Now work out that buffer! (without blowing your storage quota)*

**Contributors:  [tobbez![<3](http://i.imgur.com/kX2q6Bm.png)](https://what.cd/user.php?id=605)  [evanjd/notarebel![<3](http://i.imgur.com/kX2q6Bm.png)](https://what.cd/user.php?id=417)  [phracker![<3](http://i.imgur.com/kX2q6Bm.png)](https://what.cd/user.php?id=260077)  [feralhosting![<3](http://i.imgur.com/kX2q6Bm.png)](https://www.feralhosting.com)**
