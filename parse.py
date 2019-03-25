#!/usr/bin/python
# -*- coding: UTF-8 -*-
# created: 05.03.2019
# author:  TOS

import logging
import glob
import cssutils
import validators
import bs4
from dateutil.parser import parse
from datetime import datetime
from turtlpy.client import TurtlClient

log = logging.getLogger(__name__)

def parsePasswords(content):

    lines = iter(content.splitlines())
    lastline = None
    passwords = []
    while True:
        try:
            body = {}
            if lastline is not None:
                body['title'] = lastline.strip(':,')
                lastline = None
            else:
                body['title'] = next(lines).strip(':,')
            if body['title'].lower().startswith('upc') and not body['title'].lower().startswith('upc con'):
                parts = body['title'].split(' ')
                body['title'] = parts[0].strip()
                body['user'] = parts[1].strip()
                body['pw'] = parts[2].strip()
                passwords.append(body)
                continue
            elif not ',' in body['title']:
                line = next(lines).strip().strip(':,')
            else:
                line = ', '.join(body['title'].split(',')[1:]).strip()
                body['title']=body['title'].split(',')[0].strip()
            if not ':' in line:
                if ',' in line:
                    parts = line.split(',')
                    body['user'] = parts[0].strip()
                    body['pw'] = parts[1].strip()
                elif body['title'].lower().strip()=='bonuscard':
                    parts = line.split(' ')
                    body['user'] = parts[0].strip()
                    body['pw'] = parts[1].strip()
                else:
                    if body['title'].lower().strip().find('alle')>0:
                        body['user'] = 'alle'
                        body['pw'] = line
                    elif body['title'].lower().strip()=='miles&more':
                        body['user'] = line
                        body['pw'] = ""
                    elif body['title'].lower().strip() in ['vtx','mieter verband','swisspass',
                                                           'sbb','tuenti','helsana','axa',
                                                           'travelcash','nzz','paypal',
                                                           'postfinapp', 'upc connectbox',
                                                           'helblingbl','tplink repeater']:
                        body['user'] = ""
                        body['pw'] = line
                    else:
                        body['user'] = line
                        body['pw'] = next(lines)
            else:
                while ':' in line:
                    parts = line.split(':')
                    if parts[0].strip().lower() in ['username','user']:
                        body['user'] = parts[1].strip()
                    elif parts[0].strip().lower() in ['password','pw']:
                        body['pw'] = parts[1].strip()
                    else:
                        body[parts[0].strip().lower()] = parts[1].strip()
                    line = next(lines)
                    lastline = line
            passwords.append(body)
        except StopIteration:
            break

    return passwords

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    with TurtlClient("http://<server-url>", "<username>", "<password>") as client:

        files = glob.glob("input/*.html")

        log.info("found {} notes!".format(len(files)))

        now = datetime.now()

        for file in files:
            log.info(file)
            with open(file, mode='r', encoding='utf-8') as fp:
                soup = bs4.BeautifulSoup(fp.read().replace('\n','').replace('- ','* '), "html.parser")
            googDate = int(parse(soup.select('.heading')[0].getText().strip()).timestamp())

            # Get title
            if len(soup.select('.title')) == 0:
                title = ''
            else:
                title = soup.select('.title')[0].getText()

            # selectors = {}
            # for styles in soup.select('style'):
            #     css = cssutils.parseString(styles.encode_contents())
            #     for rule in css:
            #         if rule.type == rule.STYLE_RULE:
            #             style = rule.selectorText
            #             selectors[style] = {}
            #             for item in rule.style:
            #                 propertyname = item.name
            #                 value = item.value
            #                 selectors[style][propertyname] = value

            # Parse Content
            body = soup.find("body")
            note = next(body.children)

            html = soup.select(".content")[0]


            bullets = html.select(".bullet")
            first = True
            for bullet in bullets:
                if bullet.get_text() == '☐':
                    if first:
                        bullet.replace_with(" - [ ] ")
                        first = False
                    else:
                        bullet.replace_with("- [ ] ")
                elif bullet.get_text() == '☑':
                    bullet.replace_with("- [x] ")


            listitems = html.select(".listitem")
            for listitem in listitems:
                listitem.append('\n')
                listitem.unwrap()


            tags = soup.select(".chips")
            if len(tags) > 0:
                tags = tags[0]
                tags = tags.select(".chip.label")
                tags = [tag.get_text() for tag in tags]
            else:
                tags = []


            # Convert linebreaks
            for br in soup.find_all("br"):
                br.replace_with("\n")

            content = html.getText()

            log.info("Title: {}".format(title))
            log.info("Date: {}".format(googDate))
            log.info("Tags: {}".format(tags))

            if title.lower().strip() == 'logins':
                passwords = parsePasswords(content)
                for pw in passwords:
                    log.warning("PASSWORD")
                    log.info("--> {}".format(pw))
                    board = client.get_board("Passwords")
                    note = board.create_password(pw['title'], pw['pw'], pw['user'], pw['pw'],
                                                          tags=["script", "password hint"])
                    note.mod = googDate
                    client.add_note(note)
            else:
                lines = content.splitlines()
                if len(lines)>0 and validators.url(lines[0]):
                    url = lines[0]
                    log.warning("BOOKMARK")
                    log.info("--> {}".format(content))
                    if title=="":
                        title = url
                    if len(lines)>1:
                        text = "\n".join(lines[1:])
                    else:
                        text = ""
                    board = client.get_board("Bookmarks")
                    note = board.create_bookmark(title, text, url, tags=['script'])
                    note.mod = googDate
                    client.add_note(note)

                else:
                    log.warning("TEXT")
                    log.info("Content: \n{}".format(content))
                    board = client.get_board("General")
                    note = board.create_text_note(title,content, tags=['script'])
                    note.mod = googDate
                    client.add_note(note)
