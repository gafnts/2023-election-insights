import os
import pandas as pd
from typing import Tuple
from modules import setup_logger
from modules import TwitterRequest
from datetime import datetime, timedelta

# Initialize logger.
logger = setup_logger(__name__, "logs/download_tweets.log")

'''
This program downloads tweets from the Twitter API and stores them in two
csv files. One file contains the tweets and the other contains the users
who posted them.

Since the GET_2_tweets_search_recent endpoint of the Twitter API only
allows to download tweets from the last 7 days in batches of 60 tweets 
every 15 minutes, the program is designed to download tweets in that way.

The candidates selected are the five people currently leading the polls
for the 2023 presidential elections in Guatemala. As of the Prensa Libre's
poll of May 2023, these candidates are:
'''

candidates = [
    'carlos pineda', 
    'sandra torres', 
    'edmond mulet', 
    'zury rios', 
    'manuel conde'
]

# Other request parameters.
start_date = datetime(2023, 5, 21, 14, 00)
end_date = datetime(2023, 5, 27, 13, 00)
max_results = 10
tweets_prefix = 'tw_'
users_prefix = 'us_'


class DownloadTweets:
    def __init__(
            self, 
            candidates: list[str], 
            start_date: datetime,
            end_date: datetime, 
            max_results: int,
            tweets_prefix: str, 
            users_prefix: str
        ) -> None:

        # Initialize parameters.
        self.candidates = candidates
        self.start_date = start_date
        self.end_date = end_date
        self.max_results = max_results
        self.tweets_prefix = tweets_prefix
        self.users_prefix = users_prefix

        logger.info("DownloadTweets initialized.")

    def generate_dates(self) -> "DownloadTweets":
        """
        This method generates a list of date pairs, representing each day from the 
        defined start_date to the defined end_date.
        """

        # Generate date pairs.
        delta = timedelta(days=1)
        date = self.start_date
        
        self.dates = []
        while date < self.end_date:
            next_date = date + delta
            self.dates.append(
                (date.isoformat() + "Z", next_date.isoformat() + "Z")
            )
            date = next_date
        return self

    def get_batch(
            self, candidate: str, start_date: datetime, end_date: datetime
        ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        This method downloads a batch of tweets and users for a given candidate and date 
        pair. It returns a tuple of two pd.DataFrames, one for tweets and one for users.
        """

        tweets, users = (
            TwitterRequest(
                query=candidate,
                start_time=start_date,
                end_time=end_date,
                max_results=self.max_results
            )
            .make_request()
            .tweets_to_dataframe()
            .users_to_dataframe()
            .segregate_dataframe()
            .preprocess_data(
                tweets_prefix=self.tweets_prefix,
                users_prefix=self.users_prefix
            )
        )

        # Add a column for the candidate mentioned in each tweet.
        tweets['candidato'] = candidate

        logger.info(f"Downloaded batch of {len(tweets)} tweets for candidate {candidate}.")
        return tweets, users
    
    def download_tweets(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        This method downloads all tweets and users for the defined candidates and dates.
        It returns a tuple of two pd.DataFrames, one for tweets and one for users.
        """
        
        self.generate_dates()
        logger.info(f"Generated {len(self.dates)} date pairs for tweet downloads.")

        # Collect tweets and users for each candidate.
        tweets_collector, users_collector = [], []
        for candidate in self.candidates:

            # Collect tweets and users for each date.
            dates_tweets_collector, dates_users_collector = [], []
            for start_date, end_date in self.dates:

                tweets, users = self.get_batch(candidate, start_date, end_date)
                dates_tweets_collector.append(tweets)
                dates_users_collector.append(users)

            tweets_collector.append(pd.concat(dates_tweets_collector))
            users_collector.append(pd.concat(dates_users_collector))

        self.tweets = pd.concat(tweets_collector, axis=0, ignore_index=True)
        self.users = pd.concat(users_collector, axis=0, ignore_index=True)

        logger.info(f"Downloaded a total of {len(self.tweets)} tweets and {len(self.users)} users.")
        return self.tweets, self.users


def main() -> Tuple[pd.DataFrame, pd.DataFrame]:
    try:
        from_twitter = DownloadTweets(
            candidates=candidates,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
            tweets_prefix=tweets_prefix,
            users_prefix=users_prefix
        )

        tweets, users = from_twitter.download_tweets()
        return tweets, users
    
    except Exception as e:
        logger.error(f"Failed to download tweets: {e}")
        raise e


if __name__ == "__main__":

    # Download tweets.
    tweets, users = main()

    # Create data folder if it does not exist.
    if not os.path.exists('data'):
        os.makedirs('data')

    # Check if files exist.
    tweets_exist = os.path.exists('data/tweets.csv')
    users_exist = os.path.exists('data/users.csv')

    # Save the data.
    tweets.to_csv('data/tweets.csv', mode='a', index=False, header=not tweets_exist)
    users.to_csv('data/users.csv', mode='a', index=False, header=not users_exist)

    # Log the results.
    if tweets_exist:
        logger.info("Data appended to 'data/tweets.csv' and 'data/users.csv'")
    else:
        logger.info("Data saved to 'data/tweets.csv' and 'data/users.csv'")