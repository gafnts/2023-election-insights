import tweepy
import requests
import pandas as pd
from authenticators import TwitterAuthenticator


twitter = TwitterAuthenticator()
client = tweepy.Client(bearer_token=twitter.bearer_token)


def get_tweets(query: str, start_time: str, end_time: str, max_results: int) -> requests.Response:
    query = query = f"{query} -is:retweet -is:reply"
    tweets = client.search_recent_tweets(
        query = query,
        start_time = start_time,
        end_time = end_time,
        max_results = max_results,
        tweet_fields = [
            "id", "author_id", "created_at", "text", 
            "public_metrics", "possibly_sensitive", "lang"
        ],
        user_fields = [
            "id", "username", "name", "location", "created_at", "description", 
            "profile_image_url", "verified", "public_metrics"
        ],
        expansions = [
            "author_id", "referenced_tweets.id"
        ]
    )
    return tweets


class TwitterDataCleaner:
    def __init__(self, tweets: requests.Response) -> None:
        self.tweets = tweets
        self.df = None

    def run(self) -> pd.DataFrame:
        self.extract_tweet_data()
        self.extract_user_data()
        self.segregate_data()
        tweets_df, users_df = self.clean_data()
        return tweets_df, users_df

    def extract_tweet_data(self) -> None:
        tweet_data = []
        for tweet in self.tweets.data:
            tweet_dict = {key: getattr(tweet, key) for key in tweet.data.keys()}
            public_metrics = tweet_dict.pop('public_metrics')
            tweet_dict.update(public_metrics)
            tweet_data.append(tweet_dict)

        self.df = pd.DataFrame(tweet_data)

    def extract_user_data(self) -> None:
        users = {user.id: user for user in self.tweets.includes['users']}
        for key, user in users.items():
            user_data = {f"user_{key}": getattr(user, key) for key in user.data.keys()}
            public_metrics_user = user_data.pop('user_public_metrics')
            user_data.update({f"user_{k}": v for k, v in public_metrics_user.items()})
            users[key] = user_data

        self.df['user_data'] = self.df['author_id'].apply(lambda x: users[x])

        user_columns = pd.json_normalize(self.df['user_data']).columns
        for col in user_columns:
            self.df[col] = self.df['user_data'].apply(lambda x: x.get(col, None))

        self.df = self.df.drop(columns = ['user_data'])

    def segregate_data(self) -> None:
        self.tweets_df = self.df[[
            "id", "author_id", "created_at", "text", "possibly_sensitive", "retweet_count",
            "reply_count", "like_count", "quote_count", "impression_count", "lang"
        ]]

        self.users_df = self.df[[
            "user_id", "user_username", "user_name", "user_location", "user_created_at",
            "user_description", "user_profile_image_url", "user_verified",
            "user_followers_count", "user_following_count", "user_tweet_count", "user_listed_count"
        ]]

    def clean_data(self) -> pd.DataFrame:
        prefix = "tw_"
        tweets_df = (
            self.tweets_df
            .rename(columns={
            "id": f"{prefix}tweet",
            "author_id": f"{prefix}usuario",
            "created_at": f"{prefix}fecha",
            "text": f"{prefix}texto",
            "possibly_sensitive": f"{prefix}sensitivo",
            "retweet_count": f"{prefix}retweets",
            "reply_count": f"{prefix}replies",
            "like_count": f"{prefix}likes",
            "quote_count": f"{prefix}quotes",
            "impression_count": f"{prefix}impresiones",
            "lang": f"{prefix}idioma"
            })
            .assign(tw_fecha = lambda x: pd.to_datetime(x.tw_fecha).dt.date)
        )

        prefix = "us_"
        users_df = (
            self.users_df
            .rename(columns={
                "user_id": f"{prefix}usuario",
                "user_username": f"{prefix}handle",
                "user_name": f"{prefix}nombre",
                "user_location": f"{prefix}ubicacion",
                "user_created_at": f"{prefix}fecha_creacion",
                "user_description": f"{prefix}descripcion",
                "user_profile_image_url": f"{prefix}imagen",
                "user_verified": f"{prefix}verificado",
                "user_followers_count": f"{prefix}seguidores",
                "user_following_count": f"{prefix}siguiendo",
                "user_tweet_count": f"{prefix}tweets",
                "user_listed_count": f"{prefix}listas"
            })
            .assign(us_fecha_creacion = lambda x: pd.to_datetime(x.us_fecha_creacion).dt.date)
        )

        return tweets_df, users_df