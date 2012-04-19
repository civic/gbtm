#!/usr/bin/python
#coding: utf-8

import tweepy
import re
import urllib
import urllib2
import json
import datetime
import time
import dateutil.parser
import logging
import logging.handlers


consumer_key    = ""
consumer_secret = ""
access_key      = ""
access_secret   = ""

logger = logging.getLogger("mylogger")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
#handler = logging.handlers.RotatingFileHandler("gbtm.log", maxBytes=1*1024*1024, backupCount=3)

logger.addHandler(handler)

def main():

  while True:
    url = "https://userstream.twitter.com/2/user.json"
    param = {"delimited":"length"}
    header = {}

    auth = tweepy.OAuthHandler(consumer_key,consumer_secret)
    auth.set_access_token(access_key,access_secret)
    api = tweepy.API(auth)
    me = api.me()
    #最後の自分の投稿を取得しておく
    #tweepyのAPIで取得したのと、UserStreamのJSONで多少違うので適当に直す
    last_my_tweet = {
        "created_at": str(me.status.created_at) + "+00:00", 
        "text": me.status.text}

    logger.info("my tweet:" + last_my_tweet["text"])

    #user stream start
    auth.apply_auth(url,"POST",header,param)
    req = urllib2.Request(url)
    req.add_header("Authorization",header["Authorization"])
    stream = urllib2.urlopen(req,urllib.urlencode(param),90)

    try:
      while True:
        #length-partの読み取り
        len_part = read_length_part(stream) 
        if not len_part.isdigit():
          raise Exception("len_part is not digit")

        #json partの読み取り
        t = json.loads(stream.read(int(len_part)))

        event = t.get("event")
        if event == "favorite":
          #ファボラれ
          favorite_proc(api, t)
        elif "retweeted_status" in t:
          #ReTweeted
          public_rt_proc(api, t)

        elif ("user" in t) and ("text" in t):
          #通常Tweet
          if t["user"]["screen_name"] == "civic": #自分投稿
            logger.info("my tweet:" + t["text"])
            last_my_tweet = t
          #gbtm check 
          gbtm(api, t, last_my_tweet)

    except Exception,e:
      logger.error(str(e))

    stream.close()

def read_length_part(stream):
  len_part = ""
  while True:
    c = stream.read(1)
    if c=="\n":
      break
    if c=="":
      raise Exception("read empty, retry")
    len_part += c
  return len_part.strip()

def favorite_proc(api, t):
  """
  ファボラれ処理
  """

  tweet_datetime = to_datetime(t["created_at"]) #ファボり時間
  target_datetime = to_datetime(t["target_object"]["created_at"]) #ファボラれ対象

  span = (tweet_datetime - target_datetime).seconds
  logger.info("favorited!: %s %d" % (t["source"]["screen_name"], span))
  if span < 15:
    logger.info(u"ファボッたね！")
    status = u"高速ファボられ検出！ 記録:%d秒" % (span)
    api.update_status(status);

def public_rt_proc(api, t):
  """
  公式RT処理
  """
  tweet_datetime = to_datetime(t["created_at"]) #RTされた時間
  target_datetime = to_datetime(t["retweeted_status"]["created_at"])  #RT対象
  retweeted_sn = t["retweeted_status"]["user"]["screen_name"]

  span = (tweet_datetime - target_datetime).seconds

  logger.info("Retweetd!: %s's tweet has RTed by %s in %d sec" % 
      (retweeted_sn, t["user"]["screen_name"], span))

  if span < 20 and retweeted_sn == "civic":
    logger.info(u"RT はやっ！")
    api.update_status(u"リツイートはやっ!!! 記録:%d秒" % (span));

def gbtm(api, t, last_my_tweet):
  """
  がぶてめぇ！
  """
  user = t["user"]["screen_name"]
  msg = t.get("text")

  #自分の最新のツイートが@mizuh0に非公式リツートされたとき
  if user == "mizuh0" and re.search(r'^ *RT @civic[: ]', msg) and \
      msg.find(last_my_tweet["text"]) != -1:  #Tweetを全部含む

    tweet_datetime = to_datetime(t["created_at"]) #非公式RT
    target_datetime = to_datetime(last_my_tweet["created_at"])  #自分の最新のツイート
    span = (tweet_datetime - target_datetime).seconds

    logger.info("QT in %d secs: by %s, %s" %(span, user, msg))

    if span < 15:
      logger.info("gbtm!")
      api.update_status(status = u"@mizuh0 gbtmっ!!!", in_reply_to_status_id= t["id_str"]);

def to_datetime(s):
  return dateutil.parser.parse(s)

if __name__=="__main__":
    main()
