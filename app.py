# -*- coding: utf-8 -*-
import json
import os
import sys
from contextlib import contextmanager
from flask import Flask, render_template, request, Response
from flask_session import Session
import pycodestyle
import requests


app = Flask(__name__)
sess = Session()


@contextmanager
def redirected(stdout):
    saved_stdout = sys.stdout
    sys.stdout = open(stdout, 'w+')
    yield
    sys.stdout = saved_stdout


@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == "POST" and "action" in request.json:
        if request.json["action"] in ["synchronize", "opened"]:
            after_commit_hash = request.json["pull_request"]["head"]["sha"]
            repository = request.json["repository"]["full_name"]
            author = request.json["pull_request"]["head"]["user"]["login"]
            diff_url = request.json["pull_request"]["diff_url"]
            #update_users(repository)  # Update users of the repository
            data = {
                "after_commit_hash": after_commit_hash,
                "repository": repository,
                "author": author,
                "diff_url": diff_url,
                # Dictionary with filename matched with list of results
                "results": {},
            }

            r = requests.get(diff_url)
            lines = list(r.iter_lines())
            # All the python files with additions
            files_to_analyze = []
            for i in range(len(lines)):
                line = lines[i]
                line = line.decode('ascii')
                if line[:3] == '+++':
                    if line[-2:] == "py":
                        files_to_analyze.append(line[5:])

            for file in files_to_analyze:
                r = requests.get("https://raw.githubusercontent.com/" + \
                                 repository + "/" + after_commit_hash + \
                                 "/" + file)
                with open("file_to_check.py", 'w+') as file_to_check:
                    file_to_check.write(r.text)
                checker = pycodestyle.Checker('file_to_check.py')
                with redirected(stdout='pycodestyle_result.txt'):
                    checker.check_all()
                with open("pycodestyle_result.txt", "r") as f:
                    data["results"][file] = f.readlines()
                data["results"][file] = [i.replace("file_to_check.py", file)[1:] for i in data["results"][file]]
                os.remove("file_to_check.py")
                os.remove("pycodestyle_result.txt")



            # Make the comment
            if request.json["action"] == "opened":
                comment = "Hello @" + author + "! Thanks for submitting the PR.\n\n"
            elif request.json["action"] == "synchronize":
                comment = "Hello @" + author + "! Thanks for updating the PR.\n\n"

            for file in list(data["results"].keys()):
                if len(data["results"][file]) == 0:
                    comment += " - There are no PEP8 issues in the file `" + file[1:] + "` !"
                else:
                    comment += " - In the file `" + file[1:] + "`, following are the PEP8 issues :\n"
                    comment += "```\n"
                    for issue in data["results"][file]:
                        comment += issue
                    comment += "```"
                comment += "\n\n"

            pr_number = request.json["number"]
            query = "https://api.github.com/repos/" + repository + "/issues/" + \
                    str(pr_number) + "/comments?access_token={}".format(
                        os.environ["GITHUB_TOKEN"])
            response = requests.post(query, json={"body": comment}).json()
            data["comment_response"] = response


            js = json.dumps(data)
            return Response(js, status=200, mimetype='application/json')
    else:
        return render_template('index.html')


"""
# @app.route("/student-register", methods=['GET', 'POST'])
def student_register(request):
    flag = None
    global conn, cursor
    if "LOCAL_CHECK" not in os.environ:
        msg = "Database Connection cannot be set since you are running website locally"
        msgcode = 0
        return {"web": 'index.html' , "flag":"True", "msg":msg,"msgcode":msgcode}

    if request.method == "POST":
        form_dict = request.form.to_dict()
        query = r"INSERT INTO student (f_name,l_name,email_id,roll_no,git_handle) values ('%s','%s','%s','%s','%s') " % (
            form_dict["fname"], form_dict["lname"], form_dict["emailid"], form_dict["rollno"], form_dict["githubhandle"])

        try:
            cursor.execute(query)
            conn.commit()
            mail_subject = "Successfully registered for Kharagpur Winter of Code!"
            #mail_body = 'Hello ' + form_dict["fname"] + '<br>You have been successfully registered for the <b>Kharagpur Winter of Code</b>. ' + \
            #            'Check out the <a href="http://kwoc.kossiitkgp.in/resources">Resources for KWoC</a> now.'

            mail_body = mail_body.format(form_dict['fname'])
            mail_check = send_mail(
                mail_subject, mail_body, form_dict["emailid"])
            if not mail_check:
                slack_notification("Unable to send mail to the following student :\n{}".format(
                    form_dict))
            flag="True"
            msg=form_dict["fname"] + ", You have been successfully registered. Please check your email for instructions."
            msgcode=1
            return {"web": 'index.html' , "flag":flag, "msg":msg,"msgcode":msgcode}
        except psycopg2.IntegrityError:
            conn.rollback()
            error_msg = "{}\n\nForm : {}".format(
                traceback.format_exc(), form_dict)
            slack_notification(error_msg)
            flag="True"
            msg="Registration Failed ! User already registered"
            msgcode=0
            return {"web": 'index.html' , "flag":flag, "msg":msg,"msgcode":msgcode}
        except:
            conn.rollback()
            error_msg = "{}\n\nForm : {}".format(
                traceback.format_exc(), form_dict)
            slack_notification(error_msg)
            flag="True"
            msg="Registration Failed ! Please try again."
            msgcode=0
            return {"web": 'index.html' , "flag":flag, "msg":msg,"msgcode":msgcode}
"""

app.secret_key = os.environ["APP_SECRET_KEY"]
app.config['SESSION_TYPE'] = 'filesystem'

sess.init_app(app)
app.debug = True
# app.run()
