# ESEO Marks Tracker

A python script to track the marks for the students at ESEO Engineering School.
It will search for some new marks and send an email if some new marks are found.

## Required

### Installation

* chromedriver need to be installed
* pip install requests
* pip install mailjet_rest
* pip install selenium

### Mailjet account

THe scipt use mailjet to send the "new marks" notification, so you need to create a [Mailjet](https://app.mailjet.com/signup) account if you don't already have one.

## Before first run

The config.json file need to be completed: 
* eseo_email : the email address used to log in the eseo sharepoint
* eseo_password : the password used to log in the eseo sharepoint
* mailjet_api_key : the api key provided by mailjet
* mailjet_api_secret : the api secret provided by mailjet
* mailjet_from : the address used to send email from mailjet
* mailjet_to : the address to which one you want to receive the notifications
* your_name : quite explicit

### json_marks_id

To find this value you need to go to the sharepoint, the open the inspector and go in the network tab.
Then load the "Mes notes" page, and clic on the semester for which one you want to track the marks.
There you should find a file named with a 5 digit value, just whrite theese values for json_marks_id.
![How to find json_marks_id](https://github.com/oxyeez/ESEO-Marks-Tracker/blob/main/img/json_marks_id.png?raw=true)

## Then

Then everything should be ready, in the first run the actual marks will be grabed and store because there is nothing to compare.
Every next run the stored marks will be compared with the actual ones, and if there is a new mark, an email will be sent.
You can schedule the execution of the script with a cron job and you will receive an email notification each time a new mark is added to your remote marks sheet.