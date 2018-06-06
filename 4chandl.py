

import urllib2
import sys
import os
import traceback
import re
import urllib2
from timeit import default_timer as timer
import argparse


def main():
    userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
    imgReg = "\/\/is[1-3]\.4chan\.org\/[a-z]{1,6}\/[a-z|0-9]+\.(?:gif|jpeg|webm)"

    parser = argparse.ArgumentParser(
        description='Downloads all media from a 4chan thread.')
    parser.add_argument('url', metavar='URL', type=str,
                        help='a link to the thread like https://boards.4chan.org/gif/thread/12891600/threadname')

    args = parser.parse_args()

    #url = 'https://boards.4chan.org/gif/thread/12891600/1010-bodies-and-face'
    url = args.url

    location_of_thread_substring_in_url = url.find("thread")

    if location_of_thread_substring_in_url == -1:
        print("URL has to be 4chan thread url")
        exit(1)

    location_of_backslash_after_thread_number = url.find(
        "/", location_of_thread_substring_in_url+len("thread")+1)

    thread_number_str = url[location_of_thread_substring_in_url +
                            len("thread")+1:location_of_backslash_after_thread_number]
    print ("Thread number: "+thread_number_str)

    try:
        opener = urllib2.build_opener()
        opener.addheaders = [('User-Agent', userAgent)]

        begin_download_time = timer()
        response = opener.open(url)
        html = response.read()
        end_download_time = timer()
        print("Downloaded '"+url+"' in " +
              str(end_download_time - begin_download_time)+" ms")

        #print (html)

        begin_match_time = timer()
        p = re.compile(imgReg)
        matches = p.findall(html)
        matches = list(set(matches))
        end_match_time = timer()
        print("Parsing finished in "+str(end_match_time - begin_match_time)+" ms")
        print("Found "+str(len(matches))+" media urls")

        ensure_dir(thread_number_str)

        i = 0
        for match in matches:
            opener2 = urllib2.build_opener()
            opener2.addheaders = [('User-Agent', userAgent)]
            fullImgUrl = "https:"+str(match)
            print(fullImgUrl)
            response2 = opener2.open(fullImgUrl)
            with open(thread_number_str+"/safsadfsfasdf"+str(i)+".jpg", 'wb') as fout:
                fout.write(response2.read())
            i = i+1
    except urllib2.HTTPError as err:
        print (err)
        print (err.msg)
        sys.exit(1)


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


if __name__ == "__main__":
    main()
