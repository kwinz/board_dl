#!python
# -*- coding: utf8 -*-
# PYTHON_ARGCOMPLETE_OK


import sys
assert sys.version_info >= (
    3, 6), "Needs to be executed with python 3.6 or later"

import urllib3
import sys
import os
import traceback
import re
from timeit import default_timer as timer
import argparse
from multiprocessing import Process, Queue
import certifi
from pathlib import Path
import datetime
import subprocess
import time
import html
from tkinter import Tk, TclError
import codecs

userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
# imgReg = r"(\/\/is[1-3]\.4chan\.org\/[a-z]{1,6}\/[a-z|0-9]+\.(?:gif|jpg|webm))\" target=\"_blank\">([^<].*?)<\/a>"
imgReg = r"<a (?:title=\"([^\"]*?)\" )*href=\"(\/\/(?:s|is[1-3]|i)\.(?:4cdn\.org|4chan\.org)\/[a-z]{1,6}\/[a-z|0-9]+\.(?:gif|jpg|webm|png))\" target=\"_blank\">([^<][^\"]*?)<\/a>"
# <a title="Gillian_Anderson_x_Samantha_Alexandra_04.webm" href="//is3.4chan.org/gif/1528018466350.webm" target="_blank" data-ytta-id="-">Gillian_Anderson_x_Samant(...).webm</a>
myheaders = {'User-Agent': userAgent}
logFileName = 'board_dl.log'


def main():

    parser = argparse.ArgumentParser(
        description='Downloads all media from a 4chan thread.')
    parser.add_argument('url', metavar='URL', type=str,
                        help='A link to the thread like https://boards.4chan.org/gif/thread/12891600/threadname', nargs='?')
    parser.add_argument(
        "--symlink-names", help="Creates a subdirectory 'symlinks' linking the parsed original upload filenames with the numbered media files (requires Admin on Windows)", action="store_true")
    parser.add_argument(
        "--force-download", help="Downloads the media files again overwriting existing files", action="store_true")
    parser.add_argument(
        "--after-action", type=str, help="Can be SHOW_FILES")
    parser.add_argument(
        "--until-404", help="Keeps downloading all new media until the thread dies or --retry-max is reached", action="store_true")
    parser.add_argument(
        "--retry-delay", type=check_positive, default=120, help="Delay in seconds in between download rounds. Combine with --until-404. Default=120")
    parser.add_argument(
        "--retries-max", type=check_natural, default=30, help="Max retries before we give up, even if thread is not 404 yet. 0 = no limit. Combine with --until-404. Default=30")
    parser.add_argument(
        "--save-html", type=str2bool, default=True, help="Save html file (just the raw thread file, no dependencies). Default=True")

    args = parser.parse_args()

    # url = 'https://boards.4chan.org/gif/thread/12891600/1010-bodies-and-face'

    if(args.url):
        url = args.url
    else:
        url = ""
        try:
            print("No url parameter (see --help). Trying url from clipboard")
            url = Tk().clipboard_get()
            print("Got: "+url)
        except TclError:
            print(
                "No url parameter passed and failed to get clipboard, are you running without GUI?")

    location_of_org_substring_in_url = url.find("org")
    location_of_thread_substring_in_url = url.find("thread")

    if location_of_org_substring_in_url == -1 or location_of_thread_substring_in_url == -1:
        print("URL has to be 4chan thread url")
        exit(1)

    board_str = url[location_of_org_substring_in_url +
                    4:location_of_thread_substring_in_url-1]
    print("Board: /"+board_str)

    location_of_backslash_after_thread_number = url.find(
        "/", location_of_thread_substring_in_url+len("thread")+1)

    thread_number_str = url[location_of_thread_substring_in_url +
                            len("thread")+1:location_of_backslash_after_thread_number]
    print("Thread number: "+thread_number_str)

    retries = 0

    while True:
        begin_download_time = timer()
        http_pool = urllib3.PoolManager(
            cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        response = http_pool.request('GET', url, headers=myheaders)
        end_download_time = timer()
        print("Downloaded '"+url+"' in " +
              str(end_download_time - begin_download_time)+" s")

        # print(str(response.data.decode('utf-8')))
        # exit(0)

        if response.status == 404:
            print("Thread timed out. Quitting.")
            break

        if response.status != 200:
            print("Unknown status code: "+str(response.status))
            exit(2)

        begin_match_time = timer()
        media_reg_pattern = re.compile(imgReg)

        matches = media_reg_pattern.findall(str(response.data.decode('utf-8')))
        matches = list(set(matches))

        # for match in matches:
        #    print(match)
        # exit(0)

        end_match_time = timer()
        print("Parsing finished in "+str(end_match_time - begin_match_time)+" s")
        print("Found "+str(len(matches))+" media urls")

        if args.symlink_names:
            ensure_dir(os.path.join(board_str, thread_number_str, "symlinks"))
        else:
            ensure_dir(os.path.join(board_str, thread_number_str))

        if args.save_html:
            with open(os.path.join(board_str, thread_number_str, "thread.html"), 'wb') as fout:
                fout.write(response.data)

        processes = []
        begin_download_media_time = timer()

        # https://stackoverflow.com/a/934173/643011
        # At this point matches contains unescaped unicode chars. Open file as utf-8 and write BOM to avoid following error:
        # UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f3a7' in position 362: character maps to < undefined >
        with codecs.open(os.path.join(board_str, thread_number_str, logFileName), 'w', 'utf-8-sig') as fout:
            fout.write("Time: "+str(datetime.datetime.utcnow())+"\n")
            fout.write(str(args.url)+"\n")
            fout.write("Found "+str(len(matches))+" media urls\n")
            fout.write("\n"+str(matches))

        for match in matches:
            process = Process(target=downloadAndSaveMediaFile,
                              args=(board_str, thread_number_str, match, args))
            process.start()
            processes.append(process)

        for process in processes:
            # wait for downloads to finish, but not longer than 30 minutes
            process.join(60*30)

        end_download_media_time = timer()

        print("Downloaded all media in " +
              str(end_download_media_time - begin_download_media_time)+" s")

        if args.until_404 and (args.retries_max == 0 or retries < args.retries_max):
            print("Retrying in "+str(args.retry_delay)+" s")

            # A List of Items
            items = list(range(0, args.retry_delay))
            l = len(items)

            # Initial call to print 0% progress
            printProgressBar(0, l, prefix='Progress:',
                             suffix='Complete', length=50)

            for i, _ in enumerate(items):
                # Do stuff...
                time.sleep(1)
                # Update Progress Bar
                printProgressBar(i+1, l, prefix='Progress:',
                                 suffix='Complete', length=50)
            retries += 1
        else:
            break

    if args.after_action == "SHOW_FILES":
        directory = os.path.join(board_str, thread_number_str, " ")
        print("Opening in explorer: "+str(directory))
        subprocess.Popen(r'explorer "' + directory + '"')


def downloadAndSaveMediaFile(board_str, thread_number_str, match, args):

    title_match = match[0]
    url_match = match[1]
    name_match = match[2]

    title_match = html.unescape(title_match)
    name_match = html.unescape(name_match)

    if(len(title_match) > 0):
        name_match = title_match

    # remove bad NTFS filename characters
    name_match = re.sub(r'[\/\\*?:"<>]', '_', name_match)

    fullImgUrl = "https:"+str(url_match)
    file_name = fullImgUrl[fullImgUrl.rfind("/")+1:]
    target_path = os.path.join(board_str, thread_number_str, file_name)
    name_path = os.path.join(
        board_str, thread_number_str, "symlinks", name_match)
    # print("Old name: "+name_match)
    # return 0

    my_file = Path(target_path)
    if my_file.is_file() and my_file.stat().st_size > 0:
        if args.force_download:
            print("already downloaded "+target_path +
                  " but force downloading")
            download(fullImgUrl, target_path)
        else:
            print("already downloaded "+target_path+" SKIPPING")
    else:
        download(fullImgUrl, target_path)

    if args.symlink_names:
        if not os.path.exists(name_path):
            # symlinks have to reference the original file relative to itself,
            # not relative to our current python working directory
            print("Creating link: " + str(name_path))
            os.symlink(os.path.join("..", file_name), name_path)


def download(fullImgUrl, target_path: str):
    print("Downloading: "+fullImgUrl + "\nPath: " + target_path)
    http_pool = urllib3.PoolManager(
        cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
    response = http_pool.request('GET', fullImgUrl, headers=myheaders)

    with open(target_path, 'wb') as fout:
        fout.write(response.data)


def ensure_dir(pathStr):
    print("Checking if we have to create " + str(pathStr))
    file_path = Path(pathStr)
    if not os.path.exists(file_path):
        print("Yes. Creating " + str(file_path))
        os.makedirs(file_path)
    else:
        print("No. ")

# Print iterations progress


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█'):
    """
    Call in a loop to create terminal progress bar

    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    @authors:
        https://stackoverflow.com/a/34325723/643011
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    eval(r"print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')")
    # Print New Line on Complete
    if iteration == total:
        print()


def check_positive(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(
            "%s is an invalid positive value" % value)
    return ivalue


def check_natural(value):
    ivalue = int(value)
    if ivalue < 0:
        raise argparse.ArgumentTypeError(
            "%s is an invalid natural (not negative integer value)" % value)
    return ivalue


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


if __name__ == "__main__":
    main()
