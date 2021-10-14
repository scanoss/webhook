import os
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_report_mail(config, commit_info):
    # me == my email address
    # you == recipient's email address
    text = "File    Purl    Version     Lines\n"

    if not config['user'] or not config['pass'] or not config['dest']:
        return True, "wrong email config"

    me = config['user']
    you = config['dest']

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "SCANOSS AWS report"
    msg['From'] = me
    msg['To'] = you

    # Create the body of the message (a plain-text and an HTML version).
    template_path = os.path.abspath(os.path.dirname(__file__)) + '/' + 'email_template.html'

    with open(template_path, 'r') as file:
        temp = file.read()

    html_l = string.Template(temp)
    content = ""
    users = []
    emails = []
    for commit in commit_info:
        if not commit['matches']:
            continue
        
        results = commit['matches']
        users.append(commit['user'])
        emails.append(commit['email'])
        for result in results:
            text += '    '.join(result) + '\n'
            content += """<tr class="table-success" style="" bgcolor="#f2f2f2">"""
            content += f"""<td style="line-height: 20px; font-size: 16px; margin: 0; padding: 12px; border: 1px solid #e2e8f0;" valign="top" bgcolor="#84e8ba" align="left"><a href="{commit['url']}" style="color: #0d6efd;">{commit['sha']}</a></td>"""
            content += f"""<td style="line-height: 20px; font-size: 16px; margin: 0; padding: 12px; border: 1px solid #e2e8f0;" valign="top" bgcolor="#84e8ba" align="left">{result[0]}</td>"""
            content += f"""<td style="line-height: 20px; font-size: 16px; margin: 0; padding: 12px; border: 1px solid #e2e8f0;" valign="top" bgcolor="#84e8ba" align="left">{result[1]}</td>"""
            #content += f"""<td style="line-height: 24px; font-size: 16px; margin: 0; padding: 12px; border: 1px solid #e2e8f0;" valign="top" bgcolor="#84e8ba" align="left">{result[2]}</td>"""
            content += f"""<td style="line-height: 20px; font-size: 16px; margin: 0; padding: 12px; border: 1px solid #e2e8f0;" valign="top" bgcolor="#84e8ba" align="left">{result[3]}</td>"""
            content += f"""<td style="line-height: 20px; font-size: 16px; margin: 0; padding: 12px; border: 1px solid #e2e8f0;" valign="top" bgcolor="#84e8ba" align="left"><a href="{result[4]}" style="color: #0d6efd;">{result[4].rsplit('/',1)[1]}</a></td>"""
            content += f"""<td style="line-height: 20px; font-size: 16px; margin: 0; padding: 12px; border: 1px solid #e2e8f0;" valign="top" bgcolor="#84e8ba" align="left">{result[5]}</td>"""
            content += "</tr>"
    users = list(set(users))
    emails = list(set(emails))

    html = html_l.substitute(name = ','.join(users), email = ','.join(emails), elements = content)
    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.      
    msg.attach(part1)
    msg.attach(part2)
    # Send the message via local SMTP server.
    mail = smtplib.SMTP('smtp.gmail.com', 587)
    try:
        mail.ehlo()
        mail.starttls()
        mail.login(config['user'], config['pass'])
        mail.sendmail(me, list(you.split(",")), msg.as_string())
        mail.quit()
        return False, "The email was sent"
    except Exception:
        return True, "Problem sending the email"
