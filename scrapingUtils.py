import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA #sentiment analysis using vader
import math
import datetime as dt
import numpy as np
from datetime import date
import pandas as pd
import os
import smtplib, ssl #libraries needed to send emails
import sklearn as sk

#download lexicons
nltk.download('vader_lexicon')
nltk.download('stopwords')

#Returns the average comment sentiment for a post, where each comment is determined to have either positive (= 1),
#neutral (= 0), or negative (= -1) sentiment. Although I'm not sure this is the best way to do it... but it seems reasonable.
#replace_more_limit indicates how many "Load More Comments" will be uncollapsed. After limit is hit, those collapsed comments are
#all removed
def commentSentiment(submission,replace_more_limit = 10):
    #urlT is the url of the pos
    
    subComments = []
    bodyComment = []
    
    #check first to see if the submission has any comments
    try:
        subComments = submission.comments
    except:
        return np.nan
    if len(subComments) == 0: #then there are no comments
        return np.nan
    
    #for each comment in all the main comments (i.e. not subcomments), append the entire body of the comment to bodyComment list
    #but first extract all comments which have been replaced by a "load more comments" up to a maximum limit. If limit = 0, the code
    #just removes all the hidden comments
    subComments.replace_more(limit=replace_more_limit)
    for comment in subComments:
        try: 
            bodyComment.append(comment.body)
        except:
            return 'erroneous comment found'
    
    sia = SIA() #initialize the sentiment intensity analyzer
    results = []
    
    #loop through every comment
    for line in bodyComment:
        #evaluate the Polarity Scores from the SIA
        scores = sia.polarity_scores(line)
        #scores is a dictionary with the following keys: neg, neu, pos, compound. neg, neu, and pos are fractions that sum to 1,
        #indicating the fractions of the text that is negative, neutral and positive. compound is a score from -1 to 1 that tells
        #you the overall polarity of the line where -1 is very negative and 1 is very positive.
        
        #add key 'headline' to the scores dictionary for which the entry contains the actual comment
        scores['headline'] = line
        
        #append the dictionary to a list of results
        results.append(scores)
    
    #make a dataframe where the keys (neg, neu, post, compound, headline) are the columns of the df and each individual comment 
    #has its own row
    df =pd.DataFrame.from_records(results)
    
    #add another column with the name "label" which is all 0s
    df['label'] = 0
    
    #set all rows (i.e. comments) where the compound>0.1 to a label of 1 and all where the compound<-0.1 to a label of -1
    #Basically, threshold a positive or negative comment by the 0.1 magnitude. This is slightly more stringent than the suggested
    #threshold of 0.05 by the author of the package, but it makes sense to be more conservative here.
    df.loc[df['compound'] > 0.1, 'label'] = 1
    df.loc[df['compound'] < -0.1, 'label'] = -1

    #calculate the average positive or negative comments
    averageScore = np.mean(df['label'])
    
    return(averageScore)



#Return the UTC date integer of the last made comment
def latestComment(submission,replace_more_limit = 10):
    updateDates = []
    
    try:
        subComments = submission.comments
    except:
        return np.nan
    if len(subComments) == 0: #then there are no comments
        return np.nan
    
    subComments.replace_more(limit=replace_more_limit)
    for comment in subComments:
        updateDates.append(comment.created_utc)
  
    updateDates.sort()
    return(updateDates[-1])
    

#Convert UTC date integer to a datetime date & time stamp
def get_date(date):
    if np.isnan(date):
        return np.nan
    return dt.datetime.fromtimestamp(date)

#Convert UTC date integer to a datetime time stamp
def get_time(date):
    if np.isnan(date):
        return np.nan
    return dt.datetime.fromtimestamp(date).time()

#Find num minutes ago a post was made
def postAge_minutes(post):
    DateTimePost = get_date(post.created_utc)
    DateTimeNow = dt.datetime.now()
    deltaT_DateTime = DateTimeNow-DateTimePost
    
    return deltaT_DateTime.total_seconds()/60

#Finds the projected reddit score of a post in the future
def proj_rscore(post,minutes):
    postAge = postAge_minutes(post)
    post_score = post.score
    utc_stamp = post.created_utc
    proj_rscore = utc_stamp/45000+math.log10(max(post_score/postAge*minutes,1))
    
    return proj_rscore

#Find median projected reddit score of the front page
def FP_median_proj_rscore(reddit,minutes):
    i = 0
    A = np.zeros(25)
    for post in reddit.subreddit('wallstreetbets').hot(limit=25):
         A[i] = proj_rscore(post,minutes)
         i += 1
            
    return np.median(A)

#Remove non ascii for printing text to emails
def remove_non_ascii(text):
    return ''.join([i if ord(i) < 128 else ' ' for i in text])

#Function to craft an email for a front page alert
def FP_message_crafter(reddit,posts):
    subject = """Subject: DD alert"""
    
    header = """
The following posts have reached the front page of WSB:"""
    
    message =  subject + '\n' + header
    #now add the posts that have made it to the front page
    for post in posts:
        mystring = """
%s 
%s"""
        post_title = post.title
        url = post.url
        message_post =  mystring % (post_title, url)

        message = message + '\n'+ message_post
    
    message = remove_non_ascii(message)
    return message

#Function to craft an email for a predicted front page alert
def predictedFP_message_crafter(reddit,posts,probs):
    subject = """Subject: DD alert"""
    
    header = """
The following posts are predicted to reach the front page of WSB:"""
    
    message =  subject + '\n' + header
    #now add the posts that have made it to the front page
    kk = 0
    for post in posts:
        mystring = """        
%s 
%s
probability = %.2f """
        
        post_title = post.title
        url = post.url
        prob = probs[kk]
        kk += 1
        message_post =  mystring % (post_title, url, prob)

        message = message + '\n'+ message_post
    
    message = remove_non_ascii(message)
    return message

#Function to send an email given a message
def send_email(message):
    global sender_email
    global receiver_email
    global pasword_email
    global port
    global smtp_server
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password_email)
        server.sendmail(sender_email, receiver_email, message)

#Check if any entries in DF are in front page and set FP column to 1 in that case
def check_if_on_FP(reddit):
    global DF
    print('Checking to see if posts made it to front page...')
    #now check the 25 top posts under "hot" to see whether any of these posts have attained front page status
    for post in reddit.subreddit('wallstreetbets').hot(limit=25):
        URL_post = post.url
        isinDF = (DF['url'] == URL_post).any()
        if isinDF:
            index_in_DF = DF[(DF['url'] == URL_post)].index.values[0] #this is the index of the post in our DF
            #if the FP parameter is still 0 set it to 1
            if (DF.loc[index_in_DF,'FP'] == 0):
                DF.loc[index_in_DF,'FP'] = 1 
    print('Check complete.')

#function that gets executed in the scheduled reddit scrape
def timed_reddit_scrape(reddit,isEmail=False, model = None, model_drivers = [], p_thresh = 0.5):
    global DF
    global i_on_FP
    i = 0
    current_time = dt.datetime.now().strftime("%H:%M:%S")
    print('Scraping new posts at time', current_time ,'...')
    
    probs = []
    predicted_posts = []
    
    for post in reddit.subreddit('wallstreetbets').new(limit=100):
        if (post.link_flair_text == "DD"):
            postAge = postAge_minutes(post)
            URL_post = post.url
            
            #append to DF only post is older than 30 min and newer than 35 min and if it hasn't already been appended
            if (postAge > 30) and (postAge < 35):
                if not (DF['url'] == URL_post).any():
                    i += 1
                    mydict = {}
                    mydict['FP'] = 0
                    utc_stamp = post.created_utc
                    mydict['post_date'] = get_date(utc_stamp)
                    mydict['post_age_min'] = postAge
                    mydict['url'] = URL_post
                    post_author = post.author
                    mydict['title'] = post.title
                    mydict['author'] = post_author
                    if post_author != None:
                        mydict['author_link_karma']= post_author.link_karma
                        mydict['author_comment_karma'] = post_author.comment_karma
                    post_score = post.score
                    mydict['post_score'] = post_score
                    mydict['post_upvote_ratio'] = post.upvote_ratio
                    mydict['comment_sentiment'] = commentSentiment(post)
                    mydict['num_comments'] = post.num_comments
                    mydict['proj_rscore_prem_60'] = proj_rscore(post,60)-FP_median_proj_rscore(reddit,60)
                    mydict['proj_rscore_prem_90'] = proj_rscore(post,90)-FP_median_proj_rscore(reddit,90)
                    
                    #check to see if a model has been assigned
                    isModel = False
                    if model is not None:
                        isModel = True
                        #get the probability
                        x = np.array([])
                        for driver in model_drivers:
                            x = np.append(x,mydict[driver])
                            x = x.reshape(1, -1)
                            
                        p = model.predict_proba(x)[0][1]

                        #if the probability is greater than p_thresh, store probability and post to potentially send an email alert
                        if p > p_thresh:
                            probs += [p]
                            predicted_posts += [post]
                            
                    DF = DF.append(mydict,ignore_index = True)
    
    print('Scraped',i,'new DD posts') 
    
    #prepare an email for posts predicted to reach the front page with probability >50%
    if isEmail and len(predicted_posts) > 0:
        message = predictedFP_message_crafter(reddit,predicted_posts,probs)
        print('Sending email about',len(predicted_posts),'new posts predicted to reach front page.')
        send_email(message)
    
    #now check the 25 top posts under "hot" to see whether any of these posts have attained front page status
    check_if_on_FP(reddit)
    
    #find indices in DF of posts on FP and see which are newly there
    updated_i_on_FP = DF[DF["FP"]==1].index.values
    new_i_on_FP = list(np.setdiff1d(updated_i_on_FP,i_on_FP))
    i_on_FP = updated_i_on_FP #update the global i_on_FP
    
    if isEmail is True:
        #prepare an email about the new posts on the front page
        posts = []
        for ii in new_i_on_FP:
            post_url = DF.loc[ii,"url"]
            post = reddit.submission(url=post_url)
            posts += [post]

        if len(posts)>0:
            message = FP_message_crafter(reddit,posts)
            print('Sending email about',len(posts),'new posts on front page.')
            send_email(message)
        
    print('Scrape complete.\n')
    


