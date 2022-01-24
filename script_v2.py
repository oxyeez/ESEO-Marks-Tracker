import json
import time
import os.path

import requests
from mailjet_rest import Client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from sessionStorage import SessionStorage

    
def grab_token():
    config = load_config()
    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    driver = webdriver.Chrome(options=options)
    driver.get(config["login_url"])
    

    time.sleep(5)
    email_input = driver.find_element(By.XPATH, '//*[@id="i0116"]')
    email_input.send_keys(config["eseo_email"])
    next_button = driver.find_element(By.XPATH, '//*[@id="idSIButton9"]')
    next_button.click()
    print("Email submited...")

    time.sleep(5)
    password_input = driver.find_element(By.XPATH, '//*[@id="i0118"]')
    password_input.send_keys(config["eseo_password"])
    signin_button = driver.find_element(By.XPATH, '//*[@id="idSIButton9"]')
    signin_button.click()
    print("Password submited...")

    time.sleep(5)
    stay_signed_button = driver.find_element(By.XPATH, '//*[@id="idSIButton9"]')
    stay_signed_button.click()

    time.sleep(10)
    driver.get("https://reseaueseo.sharepoint.com/sites/etu/Pages/Mes-notes.aspx")
    print("Loading \"Mes-notes\" page...")

    time.sleep(10)
    sessionStorage = SessionStorage(driver)
    keys = sessionStorage.keys()
    key = [key for key in keys if '","scopes":"' in key][0]
    item = sessionStorage.get(key)
    print("SessionStorage item grabed.")

    driver.close()

    return grab_token() if item == None else json.loads(item)["accessToken"]


def load_config():
    with open("config.json", "r") as f:
        return json.loads(f.read())


def update_headers():
    config = load_config()
    config["headers"]["Authorization"] = "Bearer " + grab_token()

    with open("config.json", "w") as f:
        f.write(json.dumps(config))


def clean_json(json):
    json_cleansed = []
    for ue in json:
        json_cleansed.append({
            "ue_name":ue["strNom"],
            "maters":[{
                        "mater_coef":mater["decCoefficient"], 
                        "mater_name":mater["strTitre"], 
                        "mater_mark":(float(mater["strValeur"].replace(",",".")) if mater["strValeur"] != "" else None)
                    } for mater in ue["Contenu"]]
            })
    return json_cleansed


def process_marks(json):
    for ue in json:
        sum_with_coef = 0
        sum_coef = 0
        for mater in ue["maters"]:
            if mater["mater_mark"] != None:
                sum_with_coef += mater["mater_mark"] * mater["mater_coef"]
                sum_coef += mater["mater_coef"]
        ue["ue_coef"] = sum_coef
        if sum_coef != 0:
            ue["ue_mean"] = round(sum_with_coef / sum_coef, 2)
        else:
            ue["ue_mean"] = None
    return json


def grab_marks_json():
    config = load_config()
    response = requests.request(method="GET", url=config["url_json_marks"] + config["json_marks_id"], headers=config["headers"])
    
    if response.status_code == 500:
        print("Need to update token")
        update_headers()
        config = load_config()
        response = requests.request(method="GET", url=config["url_json_marks"] + config["json_marks_id"], headers=config["headers"])

    return process_marks(clean_json(json.loads(response.text)))


def process_general_mean(my_json):
    sum_with_coef = 0
    sum_coef = 0
    for ue in my_json:
        if ue["ue_mean"] != None:
            sum_with_coef += ue["ue_mean"] * ue["ue_coef"]
            sum_coef += ue["ue_coef"]
    if sum_coef != 0:
        return round(sum_with_coef / sum_coef, 2)
    else:
        return None


def store_new_marks(my_json):
    with open('marks.json', 'w') as outfile:
        json.dump(my_json, outfile)


def load_old_marks():
    with open('marks.json') as json_file:
        return json.load(json_file)


def find_ue(ue_name, json):
    for ue in json :
        if ue["ue_name"] == ue_name:
            return ue
    return None


def find_mater(mater_name, json):
    for mater in json:
        if mater["mater_name"] == mater_name:
            return mater
    return None


def search_for_changes(old_json, new_json):
    changes = {}
    for ue_new in new_json:
        ue_old = find_ue(ue_new["ue_name"], old_json)
        if ue_old != None:
            for mater_new in ue_new["maters"]:
                mater_old = find_mater(mater_new["mater_name"], ue_old["maters"])
                if mater_old != None and mater_new["mater_mark"] != mater_old["mater_mark"]:
                    if ue_new["ue_name"] not in changes:
                        changes[ue_new["ue_name"]] = {"old_mean":ue_old["ue_mean"], "new_mean":ue_new["ue_mean"]}
                    changes[ue_new["ue_name"]][mater_new["mater_name"]] = {"old_mark":mater_old["mater_mark"],"new_mark":mater_new["mater_mark"]}
                elif mater_old == None and mater_new["mater_mark"] != None:
                    if ue_new["ue_name"] not in changes:
                        changes[ue_new["ue_name"]] = {"old_mean":ue_old["ue_mean"], "new_mean":ue_new["ue_mean"]}
                    changes[ue_new["ue_name"]][mater_new["mater_name"]] = {"old_mark":None,"new_mark":mater_new["mater_mark"]}
        elif ue_old == None and ue_new["ue_mean"] != None:
            changes[ue_new["ue_name"]] = {"old_mean":None, "new_mean":ue_new["ue_mean"]}
            for mater_new in ue_new["maters"]:
                changes[ue_new["ue_name"]][mater_new["mater_name"]] = {"old_mark":None,"new_mark":mater_new["mater_mark"]}
    
    return changes


def generate_html_email(changes, old_json, new_json):
    with open("email_head.html", "r", encoding='utf-8') as html_file:
        mail_body = html_file.read()
    
    mail_body += '<body><h2>Il y a des nouveautés dans le bulletin !!</h2>'
    mail_body += '<table class="tableUF"><thead><tr>'
    mail_body += '<th>Matière</th><th>Coef</th><th>Notes</th><th>Moyenne</th></tr></thead><tbody>'
    
    for ue in new_json:
        mail_body += f'<tr class="lineUE"><td class="mater" colspan="3">{str(ue["ue_name"])}</td><td class="mean" rowspan="{len(ue["maters"])+1}">'
        if ue["ue_name"] in changes:
            if changes[ue["ue_name"]]["old_mean"] != None and changes[ue["ue_name"]]["new_mean"] != None:
                mail_body += f'<span class="old">{str(changes[ue["ue_name"]]["old_mean"])}</span> -> <span class="new">{str(changes[ue["ue_name"]]["new_mean"])}</span></td></tr>'
            elif changes[ue["ue_name"]]["old_mean"] == None and changes[ue["ue_name"]]["new_mean"] != None:
                mail_body += f'<span class="new">{str(changes[ue["ue_name"]]["new_mean"])}</span></td></tr>'
            elif changes[ue["ue_name"]]["old_mean"] != None and changes[ue["ue_name"]]["new_mean"] == None:
                mail_body += f'<span class="old">{str(changes[ue["ue_name"]]["old_mean"])}</span></td></tr>'
        else:
            mail_body += f'{str(ue["ue_mean"]) if ue["ue_mean"] != None else str()}</td></tr>'
       
        for mater in ue["maters"]:
            mail_body += f'<tr><td class="eval">{mater["mater_name"]}</td>'
            mail_body += f'<td>{str(mater["mater_coef"])}</td><td>'
            if ue["ue_name"] in changes and mater["mater_name"] in changes[ue["ue_name"]]:
                if changes[ue["ue_name"]][mater["mater_name"]]["old_mark"] != None and changes[ue["ue_name"]][mater["mater_name"]]["new_mark"] != None:
                    mail_body += f'<span class="old">{str(changes[ue["ue_name"]][mater["mater_name"]]["old_mark"])}</span> -> <span class="new">{str(changes[ue["ue_name"]][mater["mater_name"]]["new_mark"])}</span></td></tr>'
                elif changes[ue["ue_name"]][mater["mater_name"]]["old_mark"] == None and changes[ue["ue_name"]][mater["mater_name"]]["new_mark"] != None:
                    mail_body += f'<span class="new">{str(changes[ue["ue_name"]][mater["mater_name"]]["new_mark"])}</span></td></tr>'
                elif changes[ue["ue_name"]][mater["mater_name"]]["old_mark"] != None and changes[ue["ue_name"]][mater["mater_name"]]["new_mark"] == None:
                    mail_body += f'<span class="old">{str(changes[ue["ue_name"]][mater["mater_name"]]["old_mark"])}</span></td></tr>'
            else:
                mail_body += f'{str(mater["mater_mark"]) if mater["mater_mark"] != None else str()}</td></tr>'
    
    mail_body += '</tbody></table><table class="tableSynthesis"><tbody><tr class="blocSynthese"><th class="blocTitleSection">Moyenne</th></tr>'
    mail_body += f'<tr><td class="blocInfosSection mean"><span class="valueSection old">{process_general_mean(old_json)}</span>/20 -> <span class="valueSection new">{process_general_mean(new_json)}</span>/20</td>'
    mail_body += '</tr></tbody></table></body>'

    return mail_body


def send_email(mail_body):
    config = load_config()
    api_key = config["mailjet_api_key"]
    api_secret = config["mailjet_api_secret"]
    mailjet = Client(auth=(api_key, api_secret), version='v3.1')
    data = {
    'Messages': [
        {
        "From": {
            "Email": config["mailjet_from"],
            "Name": "Notes Tracker"
        },
        "To": [
            {
            "Email": config["mailjet_to"],
            "Name": config["your_name"]
            }
        ],
        "Subject": "Nouvelles Notes",
        "HTMLPart": mail_body
        }
    ]
    }
    result = mailjet.send.create(data=data)
    if result.status_code != 200:
        send_email(mail_body)



def main():
    if not os.path.isfile("marks.json"):
        print("Seams that there is no old marks...\nFor this time the marks will only be loaded.")
        new_json = grab_marks_json()
        store_new_marks(new_json)

    else:
        new_json = grab_marks_json()
        old_json = load_old_marks()
        changes = search_for_changes(old_json, new_json)

        if changes:
            print("Find some new marks !!")
            body = generate_html_email(changes, old_json, new_json)
            send_email(body)
            print("Notification sent.")
            store_new_marks(new_json)
        else:
            print("No new marks found.")


main()