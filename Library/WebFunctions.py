#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Jackrabbit AI
# 2021 Copyright © Robert APM Darin
# All rights reserved unconditionally.

import sys
import os
import io
import copy
import itertools
import functools
import inspect
import traceback
import datetime
import time
import random
import json
import string
import re
import requests
import pdfplumber
import youtube_transcript_api
import scrapingant_client as Ant
from playwright.sync_api import sync_playwright

import DecoratorFunctions as DF
import CoreFunctions as CF
import FileFunctions as FF

# Decode hash symbols

@DF.function_trapper(None)
def DecodeHashCodes(input_string):
    def replace_entity(match):
        # Extract the numeric value from the match
        entity_code = match.group(1)
        try:
            # Convert the numeric value to a character
            return chr(int(entity_code))
        except ValueError:
            # Return the original match if conversion fails
            return match.group(0)

    # Regular expression to match numeric character references (e.g., &#65;)
    entity_pattern = r'&#(\d+);'
    return re.sub(entity_pattern, replace_entity, input_string)

# The `yttags2text` function extracts tags from a YouTube video by
# analyzing its URL to find the video ID. It then uses YouTube's API to
# fetch details about the video, including its tags. If tags are available,
# it returns them as a simple list. If the video can't be found or has no
# tags, it returns a placeholder message. This process ensures the tags are
# easily accessible from any valid YouTube link.

@DF.function_trapper('{[(*VNF*)]}')
def yttags2text(url,userhome=None):
    def extract_video_id(url):
        # Match either a youtu.be or youtube.com URL to extract the video ID
        youtube_regex=r"(?:youtu\.be\/|youtube\.com\/(?:.*v=|.*\/|.*v\/|.*embed\/|.*shorts\/))([a-zA-Z0-9_-]{11})"
        match=re.search(youtube_regex, url)

        if match:
            return match.group(1)
        else:
            return None

    def get_video_tags(video_id):
        # Fetch video details including tags
        try:
            request=youtube.videos().list(
                part="snippet",
                id=video_id
            )
        except Exception as err:
            print(f"Broke yttags: {sys.exc_info()[-1].tb_lineno}/{err}")
            return '{[(*VNF*)]}'

        response=request.execute()

        if "items" in response and len(response["items"])>0:
            video_snippet=response["items"][0]["snippet"]
            if "tags" in video_snippet:
                tags=video_snippet["tags"]
                return tags
            else:
                return None
        else:
            # Video (tags) Not Found
            return '{[(*VNF*)]}'

    # Read Tokens
    Tokens=FF.ReadTokens(userhome=userhome)

    # Create YouTube Object
    youtube=build('youtube', 'v3', developerKey=Tokens['YouTube'])

    # Retrieve and display tags
    tags=get_video_tags(extract_video_id(url))

    if isinstance(tags, list):
        return '\n'.join(tags)
    return tags

# The `youtube2text` function takes a YouTube video link, extracts its ID,
# and fetches its transcript. It combines the transcript into a readable
# format and returns it as a simple text summary starting with "Video
# Transcript:".

@DF.function_trapper(None)
def youtube2text(video_url,retry=3):
    # Extract the video ID from the URL
    #video_id=video_url.split('v=')[1]
    video_id=re.search(r'(v=|be/|embed/|v/|youtu\.be/|\/videos\/|\/shorts\/|\/watch\?v=|\/watch\?si=|\/watch\?.*?&v=)([a-zA-Z0-9_-]{11})',video_url).group(2)

    # Fetch the transcript using the YouTubeTranscriptApi
    transcript_list=[]
    c=0
    while c<retry:
        try:
            transcript_list=youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
            c=retry+1
        except Exception as err:
            #print("ERROR",err)
            time.sleep(3)
        c+=1

    if not transcript_list or transcript_list==[]:
        return None

    # Use the TextFormatter to convert the transcript into plain text
    transcript_text='\n'.join(line['text'] for line in transcript_list)

    return 'Video Transcript: '+transcript_text

# The `PDF2Text` function processes a PDF file and extracts its text
# content. It reads the PDF from a given buffer, retrieves the text from
# all pages, and combines it into a single string prefixed with "PDF
# Content:".

@DF.function_trapper(None)
def PDF2Text(pdf_buffer):
    with pdfplumber.open(io.BytesIO(pdf_buffer)) as pdf:
        text=""
        for page in pdf.pages:
            text+=page.extract_text()
        return 'PDF Content: '+text

# Call ScrapingAnt service to fetch web page

@DF.function_trapper(None)
def ScrapingAnt(url,userhome=None):
    # Read Tokens
    Tokens=FF.ReadTokens(userhome=userhome)

    try:
        client = Ant.ScrapingAntClient(token=Tokens['ScrapingAnt'])
        result = client.general_request(url)
    except Exception as err:
        return None
    return result.content

# Strip HTML code from buffer

def StripHTML(htmlbuf):
    # Remove the entire head section
    html=re.sub(r'<head.*?>.*?</head>', '', htmlbuf, flags=re.DOTALL)

    # Remove script and style elements
    html=re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.DOTALL)

    # Reduce <a> elements to their text content
    html=re.sub(r'<a[^>]*>(.*?)</a>', r'\1', html, flags=re.DOTALL)

    # Remove all other HTML tags
    text=re.sub(r'<[^>]+>', '', html)

    # Remove extra whitespace
    text=re.sub(r'\s+', ' ', text).strip()
    return text

# The `html2text` function is used to fetch and convert the content of a
# web page into plain text. First, it sets a user agent to mimic a browser
# request to the given URL. If the URL points to a YouTube video, it
# retrieves the video's transcript using the `youtube2text` function. For
# other types of pages, it makes an HTTP request to fetch the HTML content.
# The function handles errors gracefully, such as when a page is not found
# or if there is an issue with the URL. It checks if the content is a PDF
# and converts it to text if it is. Then, it processes the HTML by removing
# the head section, script, and style elements, and strips out other
# unnecessary HTML tags. The result is a cleaned-up, plain-text version of
# the web page, with extra whitespace removed. The function prints the
# length of the content fetched and returns it as a readable string.

# internal selcts the internal method of reading a web page. If not internal, then the
# function skips to Scraping Ant. This is useful for site that require cookies or
# JavaScript (a serverless browser).

#@DF.function_trapper(None)
def html2text(url,internal=True,external=True,userhome=None,raw=False):
    # Set the user agent
    userAgent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    headers={'User-Agent': userAgent}

    # Video transcript?
    if 'youtube.com/watch' in url or 'youtu.be/' in url:
        input_text=youtube2text(url)
        return input_text

    # Not a YouTube transcript, Fetch the HTML content from the URL

    html=None
    if internal:
        try:
#           Doesn't work well because of JavaScript
#            req=requests.get(url, headers=headers,timeout=60)
#            if req.status_code!=200:
#                html=None
#            else:
#                html=req.content

            # Headless browser
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context(user_agent=userAgent)
                page = context.new_page()
                page.set_default_timeout(60*1000)
                page.goto(url)
                html=page.content()
                browser.close()
        except Exception as err:
            html=None

    if not html:
        if external==True:
            html=ScrapingAnt(url,userhome=userhome)
            if not html:
                return None
            # Convert to bytes
    #        html=html.encode('utf-8',errors='ignore')
            if not html:
                return None
        else:
            return None

    # Check for PDF signature
    if html and html[:5]=='%PDF-':
        # MUST be type bytes
        if type(html) is not bytes:
            html=html.encode('utf-8',errors='ignore')
        text=PDF2Text(html).strip()
        print("PDF:",len(text),url)
        return text

    # Decoding (if needed) MUST be done AFTER pdf test
    if type(html) is bytes:
        html=DecodeHashCodes(html.decode('utf-8',errors='ignore'))

    # When served raw, serve only html
    if raw:
        return html

    text=StripHTML(html).strip()
    if text=='':
        return None

    return 'Web Page Content: '+text

def url2html(url, internal=True,external=True,userhome=None):
    # Set the user agent
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    # Not a YouTube transcript, Fetch the HTML content from the URL

    html=None
    if internal:
        try:
            req=requests.get(url, headers=headers,timeout=60)
            if req.status_code!=200:
                html=None
            else:
                html=req.content
        except Exception as err:
            html=None

    if not html and external==True:
        html=ScrapingAnt(url,userhome=userhome)
        if not html:
            return None
        # Convert to bytes
        html=html.encode('utf-8',errors='ignore')
        if not html:
            return None

    # Decoding MUST be done AFTER pdf test
    if html:
        html=DecodeHashCodes(html.decode('utf-8',errors='ignore'))

    return html

###
### Functions for AbuseIPDB
###

# This set of functions works together to identify potentially harmful or
# suspicious links in messages. It checks if a link is on a safe list or a
# known scam list. If the link isn’t on either list, it looks up its background
# using a service called AbuseIPDB, which evaluates whether the link’s
# associated IP address has been reported for malicious activity. If the link
# is flagged as dangerous, it’s marked as unsafe. This helps ensure that
# harmful links can be quickly identified and dealt with.

@DF.function_trapper
def ExtractURLs(text):
    url_pattern=re.compile(r"https?://[^\s]+")
    return url_pattern.findall(text)

@DF.function_trapper
def Domain2IP(domain):
    try:
        ip_address=socket.gethostbyname(domain)
        return ip_address
    except Exception as err:
        pass
    return None

@DF.function_trapper
def ExtractDomains(url):
    parsed_url=urlparse(url)
    return parsed_url.netloc

@DF.function_trapper
def CheckAbuseIPDB(domain,userhome=None):
    ipa=Domain2IP(domain)
    if ipa==None:
        return None,0
    # Read Tokens
    Tokens=FF.ReadTokens(userhome=userhome)

    url=f"https://api.abuseipdb.com/api/v2/check"
    params={"ipAddress": ipa}
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
             "Key": Tokens['AbuseIPDB'], "Accept": "application/json"}

    try:
        response=requests.get(url, headers=headers, params=params,timeout=60)
        response.raise_for_status()
        data=response.json()
        if data.get("data", {}).get("abuseConfidenceScore", 0)>0:
            return True, data["data"]["abuseConfidenceScore"]
        else:
            return False, 0
    except requests.exceptions.RequestException as e:
        print(f"Error checking AbuseIPDB: {e}")
        return None, 0

