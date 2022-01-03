import hydra # config file manager
from omegaconf import DictConfig # config file reading format

import praw # reddit api handler

from markdown import Markdown
import io

import argparse

import requests

import logging

from datetime import datetime

#region Markdown strip format setup
# From stackoverflow https://stackoverflow.com/a/54923798/10221754
def unmark_element(elem, stream=None):
    if stream is None:
        stream = io.StringIO()
    if elem.text:
        stream.write(elem.text)
    for sub in elem:
        unmark_element(sub, stream)
    if elem.tail:
        stream.write(elem.tail)
    return stream.getvalue()
Markdown.output_formats['plain'] = unmark_element
__md = Markdown(output_format="plain")
__md.stripTopLevelTags = False

def unmark(text):
    return __md.convert(text)
#endregion

logging.basicConfig(
    filename="log.txt",
    filemode="w+",
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S'
)

def get_widget_data():
    res = requests.get("https://api.climateclock.world/v1/clock?device=widget")
    if res.status_code != 200:
        logging.error(f"get_widget_data: status code {res.status_code}")

    json = None
    try:
        json = res.json()
    except:
        logging.error(f"get_widget_data: invalid json: {res.text}")
        return None

    out = {
        "carbon": json["data"]["modules"]["carbon_deadline_1"],
        "renewables": json["data"]["modules"]["renewables_1"],
        "newsfeed": json["data"]["modules"]["newsfeed_1"],
        "gcf": json["data"]["modules"]["green_climate_fund_1"],
        "indie": json["data"]["modules"]["indigenous_land_1"],
    }
    out["deadline"] = datetime.fromisoformat(out["carbon"]["timestamp"])
    return out


def format_newsfeed(widget_data = None, max_news = 5):
    if widget_data is None:
        widget_data = get_widget_data()
        if widget_data is None:
            return None

    return "\n\n".join([
        f"{news['source']}: [{news['headline']}]({news['link']})"
        for news
        in widget_data["newsfeed"]["newsfeed"]
    ][:max_news])

def format_deadline(widget_data = None):
    if widget_data is None:
        widget_data = get_widget_data()
        if widget_data is None:
            return None

    description = widget_data["carbon"]["description"]
    delta = widget_data["deadline"] - datetime.now(tz=widget_data['deadline'].tzinfo)
    years = delta.days//365
    days = delta.days % 365
    hours = delta.seconds // (60 * 60)
    minutes = delta.seconds // 60 % 60
    seconds = delta.seconds % 60
    return f"{description}:\n{years} years, {days} days, {hours:02}:{minutes:02}:{seconds:02}"


def format_gcf(widget_data = None):
    if widget_data is None:
        widget_data = get_widget_data()
        if widget_data is None:
            return None

    description = widget_data["gcf"]["description"]
    usd = widget_data["gcf"]["initial"]
    return f"{description}:\n${usd} billion"

def format_indie(widget_data = None):
    if widget_data is None:
        widget_data = get_widget_data()
        if widget_data is None:
            return None

    description = widget_data["indie"]["description"][:-1]
    km2 = int(widget_data["indie"]["initial"]) * 1_000_000
    return f"{description}:\n{km2:,} km^2"

def format_renewables(widget_data = None):
    if widget_data is None:
        widget_data = get_widget_data()
        if widget_data is None:
            return None

    description = widget_data["renewables"]["description"][:-1]
    km2 = int(widget_data["renewables"]["initial"])
    return f"{description}:\n{km2}%"

def format_all(widget_data = None):
    if widget_data is None:
        widget_data = get_widget_data()
        if widget_data is None:
            return None

    deadline = format_deadline(widget_data)
    renewables = format_renewables(widget_data)
    gcf = format_gcf(widget_data)
    indie = format_indie(widget_data)
    news = format_newsfeed(widget_data)
    return f"{deadline}\n\n{renewables}\n\n{gcf}\n\n{indie}\n\nNews: \n\n{news}"


@hydra.main(config_path="config", config_name="config")
def main(cfg: DictConfig):
    print("Loading config...")

    #region Config reading
    version = cfg['application']['version']
    name = cfg['application']['name']

    author_username = cfg['application']['author']['username']
    author_reddit_handle = cfg['application']['author']['reddit_handle']

    client_id = cfg['praw']['client_id']
    client_secret = cfg['praw']['client_secret']
    username = cfg['praw']['username']
    password = cfg['praw']['password']
    subreddits = cfg['praw']['subreddits']
    #endregion
    
    print("Creating reddit client...")

    reddit = praw.Reddit(
        client_id = client_id,
        client_secret = client_secret,
        username = username,
        password = password,
        user_agent=f"script:{name}:u/{username}:v{version} (by {author_username} {author_reddit_handle})"
    )

    print("Listening for comments...")
    subreddit = reddit.subreddit("+".join(subreddits))
    for comment in subreddit.stream.comments(skip_existing=True):
        print("Received comment. Parsing...")
        body = unmark(comment.body)
        reply_type = None
        if body == "!climateclock all":
            reply = format_all()
            if reply is not None:
                comment.reply(reply)
        elif body in [
            "!climateclock feed",
            "!climateclock newsfeed",
            "!climateclock news",
        ]:
            reply_type = "feed"
            reply = format_newsfeed()
            if reply is not None:
                comment.reply(reply)
        elif body in [
            "!climateclock",
            "!climateclock deadline",
        ]:
            reply_type = "deadline"
            reply = format_deadline()
            if reply is not None:
                comment.reply(reply)
        elif body in [
            "!climateclock gcf",
            "!climateclock green climate fund",
            "!climateclock climate fund",
        ]:
            reply_type = "gcf"
            reply = format_gcf()
            if reply is not None:
                comment.reply(reply)
        elif body in [
            "!climateclock indigenous",
            "!climateclock indie",
        ]:
            reply_type = "indie"
            reply = format_indie()
            if reply is not None:
                comment.reply(reply)
        elif body in [
            "!climateclock renewables",
            "!climateclock renewable",
        ]:
            reply_type = "renewables"
            reply = format_renewables()
            if reply is not None:
                comment.reply(reply)

        if reply_type is not None:
            print("Parsed command, replied.")
            logging.info(f"main: {reply_type}: {comment.permalink}")


if __name__ == "__main__":
    main()
