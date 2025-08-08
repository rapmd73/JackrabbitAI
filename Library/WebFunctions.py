#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Jackrabbit AI
# 2021-2025 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# This Python code is a comprehensive toolkit designed to extract, process, and
# analyze text content from various sources, including web pages, YouTube
# videos, PDFs, and more. It also includes functionality to check the safety of
# URLs by querying a database of known abusive IP addresses.

# The code begins by importing numerous libraries and modules necessary for its
# operations, such as handling web requests, parsing HTML, processing PDFs, and
# managing YouTube transcripts. It also imports custom modules like
# `DecoratorFunctions`, `CoreFunctions`, and `FileFunctions`, which likely
# contain utility functions used throughout the script.

# One of the key functions, `DecodeHashCodes`, is responsible for decoding
# numeric character references (e.g., `&#65;`) in a string and replacing them
# with their corresponding characters. This is useful for handling HTML
# entities and ensuring text is properly formatted.

# The `yttags2text` function extracts tags from a YouTube video by analyzing
# its URL, fetching video details using the YouTube API, and returning the tags
# as a list. If the video cannot be found or has no tags, it returns a
# placeholder message.

# `youtube2text` is another YouTube-related function that extracts and returns
# the transcript of a YouTube video. It handles potential errors by retrying
# the transcript fetch a specified number of times.

# For PDF files, the `PDF2Text` function processes a PDF buffer, extracts text
# from all pages, and returns it as a single string prefixed with "PDF
# Content:".

# The `ScrapingAnt` function uses the ScrapingAnt API to scrape content from a
# specified URL. It reads API tokens, creates a ScrapingAnt client, and returns
# the content of the response. If an error occurs, it returns `None`.

# `StripHTML` is a utility function that takes an HTML string, removes various
# HTML elements like `<head>`, `<script>`, and `<style>`, and extracts plain
# text. It also removes extra whitespace and trims the text for a clean output.

# The `html2text` function is a versatile tool that extracts text content from
# a given URL. It handles different types of content, including YouTube
# transcripts, PDFs, and standard web pages. Depending on the input, it uses
# internal browser instances or external scraping services to fetch content. It
# also offers customization options like `internal`, `external`, `userhome`,
# and `raw` to tailor its behavior.

# The script then introduces a set of functions related to identifying
# potentially harmful links. `ExtractURLs` finds all URLs in a given text using
# a regular expression. `Domain2IP` resolves a domain name to its IP address.
# `ExtractDomains` extracts the domain from a URL. `CheckAbuseIPDB` checks if a
# domain's IP address is reported as abusive on AbuseIPDB, a database of known
# abusive IPs.

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
from bs4 import BeautifulSoup

import DecoratorFunctions as DF
import CoreFunctions as CF
import FileFunctions as FF

# The `DecodeHashCodes` function takes an input string and decodes any numeric
# character references (e.g., `&#65;`) it contains, replacing them with their
# corresponding characters. It uses a regular expression (`&#(\d+);`) to match
# these references, and a nested function `replace_entity` to convert the
# matched numeric values to characters using the `chr` function. If a
# conversion fails (e.g., due to an invalid numeric value), the original match
# is returned unchanged. The decoded string is then returned as the result,
# effectively converting HTML entity codes to their corresponding characters.

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
    video_id=re.search(r'(v=|be/|embed/|v/|youtu\.be/|\/videos\/|\/shorts\/|\/watch\?v=|\/watch\?si=|\/watch\?.*?&v=)([a-zA-Z0-9_-]{11})',video_url).group(2)

    # Fetch the transcript using the YouTubeTranscriptApi
    transcript_list=[]
    c=0
    while c<retry:
        try:
            ytt_api=youtube_transcript_api.YouTubeTranscriptApi()
            transcript_list=ytt_api.fetch(video_id)

            c=retry+1
        except Exception as err:
            print("ERROR",err)
            time.sleep(3)
        c+=1

    if not transcript_list or transcript_list==[]:
        return None

    # Use the TextFormatter to convert the transcript into plain text

    transcript_text=''
    for snippet in transcript_list:
        transcript_text+=snippet.text+'\n'

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

# The `ScrapingAnt` function is designed to scrape content from a specified URL
# using the ScrapingAnt API. It takes two parameters: `url` (the URL to be
# scraped) and an optional `userhome` parameter, which defaults to `None`. The
# function reads tokens from a file or storage using the `FF.ReadTokens`
# method, then attempts to create a ScrapingAnt client instance with the
# retrieved token. If successful, it sends a general request to the specified
# URL and returns the content of the response. If any exception occurs during
# this process, the function catches the error and returns `None`.

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

# The `StripHTML` function takes an HTML string (`htmlbuf`) as input and
# removes various HTML elements to extract the plain text content. It first
# removes the entire `<head>` section, followed by `<script>` and `<style>`
# elements. Then, it reduces `<a>` elements to their text content, effectively
# removing the hyperlink tags. After that, it removes all remaining HTML tags,
# resulting in a plain text string. Finally, it replaces multiple whitespace
# characters with a single space and trims any leading or trailing whitespace
# before returning the extracted text. The function utilizes regular
# expressions (`re.sub`) with the `DOTALL` flag to handle multiline matches and
# ensure thorough removal of HTML elements.

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

# The `html2text` function is a versatile tool designed to extract text content
# from a given URL. It takes into account various scenarios, including YouTube
# transcripts, PDF files, and standard web pages. The function accepts several
# parameters, allowing users to customize its behavior according to their
# needs. These parameters include `internal`, `external`, `userhome`, and
# `raw`, which control how the function fetches and processes the HTML content.

# One of the key features of the `html2text` function is its ability to handle
# different types of content. If the provided URL points to a YouTube video,
# the function uses the `youtube2text` function to extract the transcript. For
# other URLs, it attempts to fetch the HTML content using either an internal
# browser instance (via Playwright) or an external scraping service
# (ScrapingAnt). If the fetched content appears to be a PDF file (based on its
# signature), the function converts it to text using the `PDF2Text` class. This
# flexibility allows the function to adapt to various input scenarios, making
# it a robust tool for text extraction.

# Once the HTML content is fetched and any necessary conversions are performed,
# the function proceeds to parse it using BeautifulSoup. It removes script and
# style tags from the HTML, as these do not contain relevant text content. The
# remaining text is then extracted and stripped of unnecessary whitespace
# characters. If the resulting text is empty, the function returns None,
# indicating that no meaningful content could be extracted from the provided
# URL. Otherwise, it normalizes the text by stripping spaces from each line and
# removing empty lines, resulting in a cleaned and more readable version of the
# original web page content.

# The `html2text` function offers several customization options through its
# parameters. The `internal` parameter controls whether an internal browser
# instance should be used for fetching HTML content, while `external`
# determines whether an external scraping service should be used as a fallback
# if internal fetching fails. The `userhome` parameter can be used when
# employing an external scraping service that requires this information for
# proper operation. Finally, setting `raw` to True causes the function to
# return only the raw HTML content without any parsing or processing, which can
# be useful for specific use cases where further custom processing is needed.
# These options allow users to tailor the behavior of the `html2text` function
# according to their specific requirements or constraints.

# The return value of the `html2text` function depends on its success in
# extracting meaningful text from the provided URL. If successful, it returns a
# string containing either raw HTML (if requested) or cleaned and normalized
# text extracted from that HTML. In cases where no meaningful text can be
# extracted (e.g., due to errors during fetching or parsing), or if specific
# conditions are met (like encountering an empty page), it may return None or
# other indicators of failure. Error handling within the function aims to catch
# exceptions during these processes and gracefully degrade when necessary steps
# cannot be completed successfully due to external factors like network errors
# or unsupported formats.

#@DF.function_trapper(None)
def html2text(url,external=False,userhome=None,raw=False):
    # Set the user agent
    userAgent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    headers={'User-Agent': userAgent}

    # Video transcript?
    if 'youtube.com/watch' in url or 'youtu.be/' in url:
        input_text=youtube2text(url)
        return input_text

    # Not a YouTube transcript, Fetch the HTML content from the URL

    html=None
    if external==True:
        html=ScrapingAnt(url,userhome=userhome)
    else:
        try:
            # If this breaks, run: playwright install
            # needs to be done after EVERY update.
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

    # Something really broke not to get anything.

    if not html:
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

    # Parse the HTML
    soup=BeautifulSoup(html,'html.parser')

    for tag in soup(['script', 'style']):
        tag.decompose()

    # Extract and print only the text content
    text=soup.get_text().strip()

    if text=='':
        return None

    # Normalize: strip spaces on each line
    lines=[line.strip() for line in text.splitlines()]
    # Remove empty lines and collapse multiple newlines to a single newline
    cleaned='\n'.join(line for line in lines if line)

    return 'Web Page Content: '+cleaned

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

# The `ExtractURLs` function takes a string input `text` and returns a list of
# all URLs found within it. It uses a regular expression pattern
# (`url_pattern`) compiled with `re.compile`, which matches both HTTP and HTTPS
# URLs by looking for strings that start with "http://" or "https://" and
# continue until a whitespace character is encountered. The `findall` method of
# the compiled pattern is then used to find all occurrences of this pattern in
# the input text, and the resulting list of URLs is returned by the function.

@DF.function_trapper
def ExtractURLs(text):
    url_pattern=re.compile(r"https?://[^\s]+")
    return url_pattern.findall(text)

# The `Domain2IP` function takes a domain name as input and attempts to resolve
# it to its corresponding IP address using the `socket.gethostbyname` method.
# If successful, it returns the IP address as a string. However, if any
# exception occurs during this process, such as a DNS resolution failure or
# network error, the function catches the exception but does not handle or log
# it, and instead returns `None`, indicating that the domain could not be
# resolved to an IP address.

@DF.function_trapper
def Domain2IP(domain):
    try:
        ip_address=socket.gethostbyname(domain)
        return ip_address
    except Exception as err:
        pass
    return None

# The `ExtractDomains` function takes a URL as input and extracts the domain
# from it. It utilizes the `urlparse` function to break down the URL into its
# components, and then returns the `netloc` attribute, which contains the
# network location (i.e., the domain) of the URL. This allows for easy
# extraction of the domain name from a given URL, excluding any path, query
# parameters, or other components. For example, if the input URL is
# "https://www.example.com/path/to/page", the function would return
# "www.example.com".

@DF.function_trapper
def ExtractDomains(url):
    parsed_url=urlparse(url)
    return parsed_url.netloc

# The `CheckAbuseIPDB` function checks if a given domain's IP address is
# reported as abusive on AbuseIPDB, a database of known abusive IP addresses.
# It first converts the domain to an IP address using the `Domain2IP` function,
# and if this fails, it returns `None` and `0`. The function then sends a GET
# request to the AbuseIPDB API with the IP address and an API key stored in
# tokens, which are read from a file using the `FF.ReadTokens` function. If the
# request is successful, it parses the JSON response and returns `True` along
# with an abuse confidence score if the IP address is reported as abusive, or
# `False` and `0` otherwise. If any error occurs during the request, it catches
# the exception, prints an error message, and returns `None` and `0`.

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
