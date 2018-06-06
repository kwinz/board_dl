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


userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
imgReg = r"\/\/is[1-3]\.4chan\.org\/[a-z]{1,6}\/[a-z|0-9]+\.(?:gif|jpg|webm)"
myheaders = {'User-Agent': userAgent}


def main():

    parser = argparse.ArgumentParser(
        description='Downloads all media from a 4chan thread.')
    parser.add_argument('url', metavar='URL', type=str,
                        help='a link to the thread like https://boards.4chan.org/gif/thread/12891600/threadname')

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
    end_match_time = timer()
    print("Parsing finished in "+str(end_match_time - begin_match_time)+" s")
    print("Found "+str(len(matches))+" media urls")

    ensure_dir(board_str+"/"+thread_number_str)

    processes = []
    begin_download_media_time = timer()
    for match in matches:
        fullImgUrl = "https:"+str(match)
        file_name = fullImgUrl[fullImgUrl.rfind("/")+1:]
        target_path = board_str+"/"+thread_number_str+"/"+file_name
        process = Process(target=downloadAndSaveMediaFile,
                          args=(fullImgUrl, target_path))
        process.start()
        processes.append(process)

    for process in processes:
        process.join()

    end_download_media_time = timer()

    print("Downloaded all media in " +
          str(end_download_media_time - begin_download_media_time)+" s")


def downloadAndSaveMediaFile(fullImgUrl, target_path):

    my_file = Path(target_path)
    if my_file.is_file() and my_file.stat().st_size > 0:
        print("already downloaded "+target_path+" SKIPPING")
        return

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
