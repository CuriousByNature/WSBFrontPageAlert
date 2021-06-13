# WSBFrontPageAlert
Get alerted when a post flaired as "DD" reaches - or is predicted to reach - the front page of the subreddit r/WallStreetBets

### Created by: Rafael (@CuriousByNature)

### Background
WallStreetBets (WSB) is a subreddit containing stock market and investing related content, including images showcasing big gains and losses from trades, memes, as well as due diligence (DD) research posts. The subreddit has grown enormously in the past year and currently has over 10 million subscribers. Since the majority of posts are memes or humorous in nature, it is easy miss the DD posts. Many DD posts contain high quality research on particular stocks and predictions for their future price movements. Given the wealth of information contained in these DD posts, it is useful to have an alert system to inform whether a new DD post has been created, and particularly, one that is perceived to be of high enough quality to reach the front page through Reddit's democratic upvote system. Here, the front page is defined to be the first 25 posts of WSB when sorted under "Hot".

WSBFrontPageAlert is a repository containing Python code which enables you to perform a scheduled scrape of WallStreetBets. The scrape, which executes at regular intervals throughout the day, searches through posts which are flaired as "DD" and are 30-35 minutes old. Several pieces of information are extracted from the post, such as its score, the author's karma, average comment sentiment, and "projected Reddit score premium" (see Features Extracted section). This information is stored in a pandas dataframe which contains all the day's DD posts. If one of these posts reaches the front page (FP) of WSB, the user has the ability to receive email alerts that indicate which DD posts have reached the front page. In addition, the user may also include a model object (from a classifier in the Scikit-Learn framework) which has been trained (using the features extracted by this scraper) to predict which posts will reach the front page. As such, the scraper will an send email alert when a post is scraped which has a high probability of reaching the front page.

### Scheduling and Scraping
Scraping of WSB is done using PRAW, the Python Redit API Wrapper (https://praw.readthedocs.io/en/latest/). To use PRAW, the user must also create a Reddit app (https://www.reddit.com/prefs/apps/) that will be operated by the code. The credentials for that app must be entered into the Configurations section in executeScraper.py. Scraping occurs in two steps:
1) New post scrape. New posts are scanned to search for DD posts which are 30-35 min old. Features from those posts are scraped and the extracted information is stored in a global dataframe "DF". If a prediction model is being used (see Predictions using Model section), an email alert (see Email Alerts section) may be sent out if the post is predicted to reach the front page. 
2) Front page scrape. The front page (top 25 posts sorted under "Hot") is scraped to see if any of the posts stored in DF have reached the front page. An email alert (see Email Alerts section) may be sent out to inform the user. 

The scraping is scheduled using the Advanced Python Scheduler (APScheduler) Python library (https://apscheduler.readthedocs.io/en/stable/). The scraping can be configured to occur at any frequency, but a frequency of 5 min is recommended in order to assure that no DD posts that are in the range of 30-35 min old are missed. In fact, there is no real advantage to scrape at a lower frequency (longer time intervals) than 5 min. Scraping can also be configured to occur up until any time during the day; here 3:30 pm is the default choice (30 min before market close) but the user may specify any time. One final check to see which DD posts have made the front page is automatically scheduled to occur 1.5 hours after the last scrape. 


### Features Extracted
The scraper extracts numerous features from each post and stores them in the global dataframe "DF" (accessed as scrapingUtils.DF):
* post_date - date and time posted
* post_age_min - age of the post in minutes
* url - URL of the post
* title - title of the post
* author - username of the author of the post
* author_link_karma - author's Reddit link karma
* author_comment_karma - author's Reddit comment karma
* post_score - score of the post (= upvotes - downvotes)
* post_upvote_ratio - ratio of upvotes to downvotes of post
* comment_sentiment - average comment sentiment for a post. Sentiment analysis is performed using the VADER sentiment analysis in the Natural Language Toolkit (https://www.nltk.org/howto/sentiment.html). Using VADER, each comment is assigned a compound sentiment score from -1 (negative sentiment) to 1 (positive sentiment). Using a threshold of +/-0.1, I assign each comment to have either positive (= 1), neutral (= 0), or negative (= -1) sentiment overall. Finally, the average of of these thresholded sentiments is returned for the comment_sentiment.
* num_comments - number of comments on post
* proj_rscore_prem_60 - projected "Reddit score premium" at 60 minutes. This is a feature I have engineered that seems to be particularly good at predicting which posts will reach the front page (see Predictions using Model section). This feature is based on Reddit's algorithm for scoring/ranking posts when sorted by "Hot". Posts are assigned a "Reddit score" based on the time they were posted and the logarithm of the post's score (= upvotes - downvotes). The details of the scoring formula can be found in several articles (e.g. https://medium.com/hacking-and-gonzo/how-reddit-ranking-algorithms-work-ef111e33d0d9). Apparently this formula has been since changed by Reddit, but in my own testing it does a pretty good job of replicating the ranking of "Hot". In this code, a slightly simplified version of the formula is used which contains all the right behaviours for posts with scores > 1. The proj_rscore_prem_60 feature is a calculation of the difference between the projected Reddit score of the post at 60 min compared to the median projected Reddit score of posts on the FP in 60 min. Projections are made by linearly extrapolating the post's score out to 60 min. Essentially, the bigger this feature is, the more likely it is that the post will score high enough to reach the FP in approximately an hour, which is a typical timescale for reaching the FP.
* proj_rscore_prem_90 - same as proj_rscore_prem_60 but with a 90 min projection horizon.

### Predictions using Model
The code has the ability to include a pickled Scikit-Learn classifier model object. Only classifiers which have a predict_proba_ method are supported. The classifier should be trained to predict whether a post will reach the FP using one or more of the features being scraped by this code. When a new DD post is scraped, the code will then compute the probability that the post will reach the front page, using the pre-trained classifier model object, based on the feature values of the post. If the probability is above a user-specified threshold, an email alert (if enabled) will be sent to notify the user. This capability is useful because it makes it possible for the user to be notified of a post that is gaining popularity before it reaches the front page.

In this repository, a sample pickled object is included (logit_model.pickle) which has been trained on the data (Data/RedditScrapeDump.csv) that I have collected over several weeks. The model is a simple logistic regression using only one feature: proj_rscore_prem_60. Despite its simplicity, the model has a cross-validation precision of around 87% and accuracy of around 95%. The training of this model is demonstrated in the Jupyter Notebook simpleLogisticRegression_FP_Predictor.ipynb. Again, this is just a sample, and I encourage users to collect more data by scraping and train more complex models. Note that if a different prediction model is used, some details must be changed accordingly in the Configurations section in executeScraper.py, including the file name of, or path to, the pickle file and a list containing the drivers of the model. Note that if the model has more than one driver, the drivers must be listed in the same order as during training.

### Email Alerts
Email alerts can be sent to the user to inform whether:
1) A 30-35 min old DD post is predicted to reach the front page (see Predictions using Model section)
2) A DD post that was previously scraped has eventually reached the front page

Email alerts are handled using the smtplib (https://docs.python.org/3/library/smtplib.html) and SSL (https://docs.python.org/3/library/ssl.html) Python libraries. The user will have to create a Gmail account to enable this feature, and, in that account, turn "Allow less secure apps" to ON. The credentials for that account must be entered into the Configurations section in executeScraper.py. More details can be found here https://realpython.com/python-send-email/, following Option 1. Note that email alerts can also be disabled in the execution code. 

### Repository Contents
* executeScraper.py - the python file that should be executed to perform the scheduled scrape. The file also contains all the configurations for the scrape (including Reddit app credentials, email bot account credentials, scheduling details, etc).
* scrapingUtils.py - a python file containing all the utility functions used for scraping and emailing alerts. This file should be left unchanged unless the user wishes to make some fundamental changes to the scraping methodology and/or features. This file is imported and used by executeScraper.py. 
* Data/RedditScrapeDump.csv - a CSV file containing nearly 350 scraped DD posts (approximately 10% of which reached FP, which is indicated by a value of 1 under the "FP" column). All aforementioned features extracted are included for each post. This data has been accumulated over several weeks of scraping. The user may use this data to do their own modelling for FP prediction and is welcome to expand this dataset with more scraping.
* simpleLogisticRegression_FP_Predictor.ipynb - a Jupyter notebook showing some sample code for training a model to predict whether a post will reach the front page. In this notebook, a single driver (proj_rscore_prem_60) logistic regression is used. Despite its simplicity, the model has a cross-validation precision of around 87% and accuracy of around 95%.
* logit_model.pickle - a pickle file containing the Scikit-Learn model object for the logistic regression classifier trained in the Jupyter Notebook above. This pickle object can be used as-is in executeScraper.py to generate FP predictions during scraping. The user is welcome to train more complex models (and save them as pickle files) in order to improve the FP prediction precision.

### Getting Started
To get started, the user must first download and install all Python library dependencies (see Dependencies section). The user must also create a Reddit app that will be operated by this code (see Scheduling and Scraping section). Finally, if the user wishes to receive email alerts, they must also create a Gmail account (see Email Alerts section).

Before executing scraping, the user must set up the Configurations section in executeScraper.py. This includes:
* Filling in their Reddit app credentials for PRAW: client_id, client_secret, user_agent
* Filling in the Gmail bot account credentials: scrapingUtils.sender_email, scrapingUtils.password_email. Also filling in the email to which alerts will be sent: scrapingUtils.receiver_email
* Modifying scraping configuration details, including the timing of the scheduled scrapes (frequency and end time), whether or not to send email alerts, and whether or not a prediction model is to be used. The pre-filled values are suggested defaults and can be left as-is to start off.

Finally, the user may simply run the python code once the above credentials have been entered. The scraping will occur at regular intervals until the specified end time. If the user wishes to run scraping again on the following day, the must re-run the python code the next day.

Note: if the user wishes to terminate the scrape before the jobs have finished, the user may either kill/restart the python kernel *or* execute the commented-out lines of code at the bottom of executeScraper.py: job.remove(), job2.remove(), sched.shutdown()

### Dependencies:
All necessary libraries are imported inside executeScraper.py and scrapingUtils.py. Most of the import libraries are standard and included in Anaconda Python. The user must install the following libraries prior to using this code:
* praw (https://praw.readthedocs.io/en/latest/)
* apscheduler (https://apscheduler.readthedocs.io/en/stable/)
* nltk (https://www.nltk.org)

