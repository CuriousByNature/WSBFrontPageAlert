import praw #reddit API
import datetime as dt
import numpy as np
from datetime import date
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler #scheduler
import os
import pickle
import sklearn as sk
import scrapingUtils #imports the scraping utility functions


############################ CONFIGURATIONS ############################


### Reddit API credentials ###

#log in to reddit using my API credentials
reddit = praw.Reddit(client_id=,
                    client_secret=,
                    user_agent=)


### email bot credentials ###

#log in to the bot
scrapingUtils.port = 465  # For SSL
scrapingUtils.smtp_server = "smtp.gmail.com"
scrapingUtils.sender_email =   # Enter the email address of your bot
scrapingUtils.receiver_email =   # Enter receiver address
scrapingUtils.password_email =  #enter password for your email bot account

### scraping configuration ###

#send email alerts?
sendEmailAlerts = True
    
#set scrape end time and frequency
end24H = 21 #the 24-hour clock hour to end scrape
endMin = 30  #the number of minutes into the hour to end scrape
scrapeFreqMin = 5 #time interval (in minutes) between scrapes

#set whether a model should be used to compute probabilities. 
#if a model is chosen, set the configuration parameters below as well.
useModel = True
modelPickleName = 'logit_model.pickle' #filename of pickle file
model_drivers = ['proj_rscore_prem_60'] #drivers to be used in model. must be one of features contained in the cols variable below
probability_threshold = 0.5 #threshold for predicting whether a post will reach front page (FP)

######################## CONFIGURATIONS END ############################



######################## Execute Scrape ################################

#load a model if specified
if useModel:
    with open(modelPickleName, 'rb') as handle:
        model = pickle.load(handle)
else:
    model = None

#load the scheduler
sched = BackgroundScheduler(daemon=True)

#create the global data frame to store all posts and their features
#first define the columns of the dataframe (i.e. features) that will be obtained during scraping [don't change this]      
cols = ['FP','post_date','post_age_min','url','title','author','author_link_karma','author_comment_karma',
                            'post_score','post_upvote_ratio','comment_sentiment','num_comments','proj_rscore_prem_60',
                            'proj_rscore_prem_90']

scrapingUtils.DF = pd.DataFrame(columns = cols)

#list of indexes in DF that have made the Front Page. Also a global variable
scrapingUtils.i_on_FP = []

#schedule the scraping job with our without a model
end_scrape = dt.datetime.combine(dt.date.today(), dt.time(end24H, endMin))
run_final_check = end_scrape + dt.timedelta(hours=1.5) #run the final check of front page 1.5 hours after last scrape

job = sched.add_job(scrapingUtils.timed_reddit_scrape,'interval', seconds = scrapeFreqMin*60, end_date = end_scrape, 
                        next_run_time=dt.datetime.now(), args=[reddit,sendEmailAlerts, model, model_drivers, probability_threshold])
    
#schedule a final job at 5 pm to check the front page once more
job2 = sched.add_job(scrapingUtils.check_if_on_FP, 'date', run_date = run_final_check, args=[reddit])

#start the scheduled jobs
timeEnd = end_scrape.strftime("%H:%M:%S")
print("Starting scheduled scraping of r/Wallstreetbets. Scraping will continue until", timeEnd)
print("\n")

sched.start()

########################################################################

### Execute the following if you want to kill the scheduled jobs before completion ###

#job.remove()
#job2.remove()
#sched.shutdown()

