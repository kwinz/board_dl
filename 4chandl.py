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


userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
#imgReg = r"(\/\/is[1-3]\.4chan\.org\/[a-z]{1,6}\/[a-z|0-9]+\.(?:gif|jpg|webm))\" target=\"_blank\">([^<].*?)<\/a>"
imgReg = r"<a (?:title=\"(.+?)\" )*href=\"(\/\/is[1-3]\.4chan\.org\/[a-z]{1,6}\/[a-z|0-9]+\.(?:gif|jpg|webm))\" target=\"_blank\">([^<].*?)<\/a>"
# <a title="Gillian_Anderson_x_Samantha_Alexandra_04.webm" href="//is3.4chan.org/gif/1528018466350.webm" target="_blank" data-ytta-id="-">Gillian_Anderson_x_Samant(...).webm</a>
myheaders = {'User-Agent': userAgent}
logFileName = 'board_dl.log'


def main():

    parser = argparse.ArgumentParser(
        description='Downloads all media from a 4chan thread.')
    parser.add_argument('url', metavar='URL', type=str,
                        help='a link to the thread like https://boards.4chan.org/gif/thread/12891600/threadname')
    parser.add_argument(
        "--symlink-names", help="creates a subdirectory 'symlinks' linking the parsed original upload filenames with the numbered media files (requires Admin on Windows)", action="store_true")
    parser.add_argument(
        "--force-download", help="downloads the media files again overwriting existing files", action="store_true")

    args = parser.parse_args()

    # url = 'https://boards.4chan.org/gif/thread/12891600/1010-bodies-and-face'
    url = args.url

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

    begin_download_time = timer()
    http_pool = urllib3.PoolManager(
        cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
    response = http_pool.request('GET', url, headers=myheaders)
    end_download_time = timer()
    print("Downloaded '"+url+"' in " +
          str(end_download_time - begin_download_time)+" s")

    # print(str(response.data))
    # exit(0)

    if response.status == 404:
        print("Thread timed out. Quitting.")
        exit(0)

    if response.status != 200:
        print("Unknown status code: "+str(response.status))
        exit(2)

    begin_match_time = timer()
    media_reg_pattern = re.compile(imgReg)

    matches = media_reg_pattern.findall(str(response.data))
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

    processes = []
    begin_download_media_time = timer()

    with open(os.path.join(board_str, thread_number_str, logFileName), 'w') as fout:
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
        process.join()

    end_download_media_time = timer()

    print("Downloaded all media in " +
          str(end_download_media_time - begin_download_media_time)+" s")


def downloadAndSaveMediaFile(board_str, thread_number_str, match, args):

    title_match = match[0]
    url_match = match[1]
    name_match = match[2]

    if(len(title_match) > 0):
        name_match = title_match

    fullImgUrl = "https:"+str(url_match)
    file_name = fullImgUrl[fullImgUrl.rfind("/")+1:]
    target_path = os.path.join(board_str, thread_number_str, file_name)
    name_path = os.path.join(
        board_str, thread_number_str, "symlinks", name_match)
    #print("Old name: "+name_match)
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
            os.symlink(os.path.join("..", file_name), name_path)


def download(fullImgUrl, target_path):
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


if __name__ == "__main__":
    main()
