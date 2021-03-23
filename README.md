# board_dl

Downloads images/videos from 4chan using Python3.6 or newer.  
* Supports original filenames.  
* Supports Unicode names.  
* Fast parallel download.  
* If no URL is passed as argument takes the URL from the clipboard.  
* Can download until 404.  
* Supports showing files when download finishes.  
* Supports HTTP and HTTPS links.  
* Tested with Windows 10 and Linux Ubuntu 18.04.  

# Usage

```
python3 ./4chandl.py --help
usage: 4chandl.py [-h] [--symlink-names] [--force-download]
                  [--after-action AFTER_ACTION] [--until-404]
                  [--retry-delay RETRY_DELAY] [--retries-max RETRIES_MAX]
                  [--save-html SAVE_HTML]
                  [URL]
 
Downloads all media from a 4chan thread.
 
positional arguments:
  URL                   A link to the thread like https://boards.4chan.org/gif/thread/12891600/threadname
 
optional arguments:
  -h, --help            show this help message and exit
  --symlink-names       Creates a subdirectory 'symlinks' linking the parsed
                        original upload filenames with the numbered media
                        files (requires Admin on Windows)  
  --force-download      Downloads the media files again overwriting existing
                        files
  --after-action AFTER_ACTION
                        Can be SHOW_FILES
  --until-404           Keeps downloading all new media until the thread dies
                        or --retry-max is reached
  --retry-delay RETRY_DELAY
                        Delay in seconds in between download rounds. Combine
                        with --until-404. Default=120
  --retries-max RETRIES_MAX
                        Max retries before we give up, even if thread is not
                        404 yet. 0 = no limit. Combine with --until-404.
                        Default=30
  --save-html SAVE_HTML
                        Save html file (just the raw thread file, no
                        dependencies). Default=True
```

# Install

You need python3 and python3-tk (e.g. `sudo apt-get install python3.7 python3-tk`)

On newer Windows 10 installs it is sufficient to install Python 3.9 from the Windows store and then packages `urllib3` and `certifi` with
`pip install -r requirements.txt`

# Debugging

Saves a `thread.html`, check with https://regex101.com/ if the `imgReg` regex in `4chandl.py` is broken due to board changes.

Logfiles: Date, url, number of urls found, [original-filename-long-optional,url,filename-short]

```
Time: 2018-06-09 16:47:33.921037
https://boards.4chan.org/trv/thread/1417871/best-longstay-cities-for-degenerate-lifestyle
Found 1 media urls

[('D71CBC8C-3CBE-4CCE-AE79-1A142C3DFC7C.jpg', '//is2.4chan.org/trv/1528553461662.jpg', 'D71CBC8C-3CBE-4CCE-AE79-1(...).jpg')]
```
