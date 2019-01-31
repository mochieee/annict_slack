#!/usr/bin/python3

import requests
import datetime
import os
import json


def month_to_season(month):
    if 1 <= month < 4:
        return "winter"
    elif 4 <= month < 7:
        return "spring"
    elif 7 <= month < 10:
        return "summer"
    else:
        return "autumn"


def get_current_qr():
    current_time = datetime.datetime.now()
    year = str(current_time.year)
    month = current_time.month
    return "-".join([year, month_to_season(month)])


def lambda_handler(event, context):
    graph_ql_query = """
    query {
        searchWorks(
        seasons: ["%s"],
        orderBy: { field: WATCHERS_COUNT, direction: DESC},
        first: 10
    ) {
        edges {
            node {
                    title
                    officialSiteUrl
                    watchersCount
                    reviewsCount
                    image {
                        recommendedImageUrl
                    }
                    reviews(
                        first: 2
                        orderBy: {field: LIKES_COUNT, direction: DESC},
                    ) {
                        edges {
                            node {
                                body
                                impressionsCount
                            }
                        }
                    }
                }
            }
        }
    }
    """ % get_current_qr()
    query = {"query": graph_ql_query}
    qb_req = requests.post(
        os.environ['ANNICT_URL'],
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(os.environ['ANNICT_KEY'])
        },
        data=query
    )
    json_raw = qb_req.json()["data"]["searchWorks"]["edges"]
    attachments = [
        {
            "color": "#36a64f",
            "pretext": "視聴者数 第{}位".format(idx + 1),
            "title": item["node"]["title"],
            "title_link": item["node"]["officialSiteUrl"],
            "image_url": item["node"]["image"]["recommendedImageUrl"],
            "thumb_url": item["node"]["image"]["recommendedImageUrl"],
            "text": "Annict 視聴者数: {}, レビュワー数: {}".format(item["node"]["watchersCount"], item["node"]["reviewsCount"]),
            "fields": [
                {
                    "title": "コメント (影響度: {})".format(comment["node"]["impressionsCount"]),
                    "value": comment["node"]["body"],
                    "short": "true"
                } for comment in item["node"]["reviews"]["edges"]
            ]
        } for idx, item in enumerate(json_raw)
    ]
    slack_message = {
        'channel': os.environ['SLACK_CHANNEL'],
        "attachments": attachments,
        'username': 'annict',
    }
    requests.post(os.environ['SLACK_WEBHOOK_URL'],
                  data=json.dumps(slack_message))
