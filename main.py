# to implement front-end data assertions
# rather than letting it fail after passing to backend
# ALL CONVERSION PUT IN FRONTEND!!!!
# - to rename alias to nickname
# - to remove chat_id references in methods
# - to shift all result strings to be returned by backend

# Needed for packaged modules if main.py run from parent directory
# https://chrisyeh96.github.io/2017/08/08/definitive-guide-python-imports.html
# https://stackoverflow.com/questions/714063/importing-modules-from-parent-folder/11158224#11158224
import os, sys; sys.path.insert(0, os.path.join(os.getcwd(), "logic"))

import constants
from time import sleep # avoid 'time' conflict in namespace
import requests
import json
import algorithm
from inspect import signature
import datetime
import signal
from assertions import *

class SIGINT_handler():
    # https://stackoverflow.com/a/43787607
    def __init__(self): self.SIGINT = False
    def handler(self, signal, frame): self.SIGINT = True

def main():
    handler = SIGINT_handler()
    signal.signal(signal.SIGINT, handler.handler)
    bot = TeleBot(True)
    
    while True:
        if handler.SIGINT: break
        bot.get_updates()
        bot.process_updates()
        sleep(0.5)
    
    bot.terminate()

def tokenize(text):
    """ Splits tokens and preserves quote-enclosed blobs """
    text = text.split('"')
    args = []
    for i in range(len(text)):
        # Quote-enclosed strings are odd-numbered
        if i % 2 == 0:
            for div in text[i].split(" "):
                if div != "": args.append(div)
        else:
            args.append(text[i])
    return args

class TeleBot:

    def __init__(self, failviolently=False):
        from unit_tests import abstractDB
        self.failviolently = failviolently
        self.token = constants.TOKEN
        self.db = algorithm.DB()
        self.url = "https://api.telegram.org/bot{}/".format(self.token)
        
        self.next_offset = None
        self.updates = None
        self.active_chats = set()
        self.start_time = datetime.datetime.now()

        self.cur_date = algorithm.DT(datetime.datetime.now()).to_date()

    def terminate(self):
        uptime = datetime.datetime.now() - self.start_time
        if uptime.days == 0:
            tss = "{} seconds".format(uptime.seconds)
        else:
            tss = "{} days".format(uptime.days)
        
        for chat_id in self.active_chats:
            self.send_message(chat_id, "Server has terminated bot.\nTotal uptime: {}.".format(tss))

    def send_message(self, chat_id, message):
        payload = {"text": message, "chat_id": chat_id}
        if "`" in message: payload["parse_mode"] = "Markdown" # auto format-detection
        requests.get(self.url + "sendMessage", params=payload)

    def retrieve_message(error_message, message):
        return error_message if bool(error_message) else message

    def get_updates(self):
        payload = {"offset": self.next_offset} # to confirm receipt of message
        r = requests.get(self.url + "getUpdates", params=payload)
        self.updates = r.json()

    def process_updates(self):
        if "result" not in self.updates: return

        # Get next offset value
        cur_offsets = list(map(lambda r: r["update_id"], self.updates["result"]))
        self.next_offset = self.next_offset if cur_offsets == [] else max(cur_offsets)+1
        
        for result in self.updates["result"]:
            if "message" not in result: continue
            if "chat" not in result["message"]: continue
            if "text" not in result["message"]: continue
            chat_id = result["message"]["chat"]["id"]
            text = result["message"]["text"]
            self.active_chats.add(chat_id)

            try:
                if text.lstrip()[0] != "/": continue # ignore non-bot-commands
                args = tokenize(text)
                cmd, args = args[0][1:], args[1:]
                if "@" in cmd: cmd = cmd.split("@")[0] # ignore calls such as /new@bot
                try:
                    assert hasattr(self, cmd), "/{} does not exist.".format(cmd)
                    response = getattr(self, cmd)(*args)
                    self.send_message(chat_id, response)
                except AssertionError as e:
                    self.send_message(chat_id, str(e))
            except BaseException as e:
                self.send_message(chat_id, "UNCAUGHT BUG!!")
                if self.failviolently: raise e
                print(e) # temporary scaffold to highlight exceptions during testing
                    
    ### COMMANDS ###

    def help(self):
        return 'Format: `/<cmd> <arguments>`\n'\
             + 'For arguments with whitespace, enclose within "".\n'\
             + 'For more help, type `/<cmd>` and follow the prompts.\n\n'\
             + 'Possible cmds:\n`new`, `edit`, `delete`, `setdate`,\n'\
             + '`add`, `present`, `late`, `absent(all)`, `report`'
            
    def hello(self):
        return "Hello World! :)"

    def prompt_qualifier(f):
        def wrapper(*args, **kwargs):
            if len(args) == 1:
                return "Please specify a qualifier, e.g. `/{} <qualifier>`".format(f.__name__)
            r = f(*args, **kwargs)
            return r
        return wrapper

    @prompt_qualifier
    def new(self, qualifier, *args):
        
        if qualifier == "member":
            inputs = "member <fullname> <section> <contact> <status>[,*<alias>]"
            assert_cmd("new", inputs, qualifier, *args)
            assert_section(args[1])
            assert_contact(args[2])
            return self.db.add_member(*args)

        if qualifier == "alias":
            inputs = "alias <curralias> <alias>[,*<alias>]"
            assert_cmd("new", inputs, qualifier, *args)
            return self.db.add_alias(*args)
        
        if qualifier == "practice":
            inputs = "practice <YYYY-MM-DD> <HH-MM> <sessiontype>"
            assert_cmd("new", inputs, qualifier, *args)
            assert_datetime(args[0], args[1])
            return self.db.add_session(*args)
        
        return "No such qualifier '{}' available.\nUse: `/new <member/alias/practice>`".format(qualifier)
                
    @prompt_qualifier         
    def delete(self, qualifier, *args):
                
        if qualifier == "member":
            inputs = "member <fullname>"
            assert_cmd("delete", inputs, qualifier, *args)
            return self.db.delete_member(*args)
                
        if qualifier == "alias":
            inputs = "alias <alias>[,*<alias>]"
            assert_cmd("delete", inputs, qualifier, *args)
            return "\n".join(map(lambda s: self.db.delete_alias(self, s), args))
                
        if qualifier == "practice":
            inputs = "practice <YYYY-MM-DD>"
            assert_cmd("delete", inputs, qualifier, *args)
            assert_date(*args)
            return self.db.delete_session(*args)

        return "No such qualifier '{}' available.\nUse: `/delete <member/alias/practice>`".format(qualifier)

    @prompt_qualifier
    def edit(self, qualifier, *args):
                
        if qualifier == "name":
            inputs = "name <oldname> <newname>[,*<alias>]"
            assert_cmd("edit", inputs, qualifier, *args)
            return self.db.update_name(*args)
                
        if qualifier == "section":
            inputs = "section <fullname> <section>"
            assert_cmd("edit", inputs, qualifier, *args)
            assert_section(args[1])
            return self.db.update_section(*args)
            
        if qualifier == "contact": # ("contact", "Full Name", "contact")
            inputs = "contact <fullname> <contact>"
            assert_cmd("edit", inputs, qualifier, *args)
            assert_contact(args[1])
            return self.db.update_contact(*args)
            
        if qualifier == "status": # ("status", "Full Name", "status")
            inputs = "status <fullname> <status>"
            assert_cmd("edit", inputs, qualifier, *args)
            return self.db.update_status(*args)

        return "No such qualifier '{}' available.\nUse: `/edit <name/section/contact/status>`".format(qualifier)

                
    ### FUNCTIONS BELOW ASSUME DATE HAS ALREADY BEEN SET VIA setdate ###

    def setdate(self, *args):
        inputs = "<YYYY-MM-DD>"
        assert_cmd("setdate", inputs, *args)
        assert_date(args[0])
        self.cur_date = algorithm.DT(args[0]).to_date()
        return "Current date is now set to {}.".format(args[0])

    def add(self, *args):
        inputs = "<alias>[,*<alias>]"
        assert_cmd("add", inputs, *args)
        if datetime.datetime.now() < self.db.get_session_dt(self.cur_date):
            return self.present(*args)
        return "\n".join(map(lambda s: self.late(s), args))

    def present(self, *args):
        inputs = "<alias>[,*<alias>]"
        assert_cmd("present", inputs, *args)
        return "\n".join(map(lambda s: self.db.set_present(self.cur_date, s), args))

    def late(self, *args):
        inputs = "<alias>[,<reason>]"
        assert_cmd("late", inputs, *args)              
        return self.db.set_late(self.cur_date, *args)

    def absent(self, *args):
        inputs = "<alias>[,<reason>]"
        assert_cmd("absent", inputs, *args)
        return self.db.set_absent(self.cur_date, *args)

    def absentall(self):
        return self.db.set_absent_all(self.cur_date)
        
    ### REPORT GENERATION ###

    def report(self, section=".", *args):
        inputs = "<section=.>[,<mode=/reason/absent/section>]"
        assert_cmd("report", inputs, section, *args)
        if section != ".": assert_section(section)
        if len(args) == 0: return self.db.get_full_report(self.cur_date, section)
        mode = args[0]
        if mode == "reason": return self.db.get_no_reason_report(self.cur_date, section)
        if mode == "absent": return self.db.get_not_present_report(self.cur_date, section)
        if mode == "section": return self.db.get_section_members(section)
        return "No such mode '{}' available.\nUse: `/report <section=.>[,<mode=/reason/absent/section>]`".format(mode)

    def print(self):
        return self.db.print()
                
if __name__ == "__main__":
    main()
