import constants
import time
import requests
import json
import algorithm
from inspect import signature
import datetime
import signal

class SIGINT_handler():
    # https://stackoverflow.com/a/43787607
    def __init__(self): self.SIGINT = False
    def handler(self, signal, frame): self.SIGINT = True

def main():
    handler = SIGINT_handler()
    signal.signal(signal.SIGINT, handler.handler)
    bot = TeleBot()
    
    while True:
        if handler.SIGINT: break
        bot.get_updates()
        bot.process_updates()
        time.sleep(0.5)
    
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

    def __init__(self):
        self.token = constants.TOKEN
        self.db = algorithm.DB()
        self.url = "https://api.telegram.org/bot{}/".format(self.token)
        
        self.next_offset = None
        self.updates = None
        self.active_chats = set()
        self.start_time = datetime.datetime.now()

        self.cur_date = datetime.datetime.now()

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
        requests.get(self.url + "sendMessage", params=payload)

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
            
            if text[0] != "/": continue # ignore non-bot-commands
            args = tokenize(text)
            cmd, args = args[0][1:], args[1:]
            try:
                assert hasattr(self, cmd), "/{} does not exist.".format(cmd)
                params = signature(getattr(self, cmd)).parameters
                skip_check = False
                for param in params.values():
                    if param.kind == param.VAR_POSITIONAL:
                        skip_check = True
                        break
                if not skip_check: assert len(params)-1 == len(args), "Expected {} arguments instead of {} in /{}.".format(len(params)-1, len(args), cmd)
            except AssertionError as e:
                self.send_message(chat_id, str(e))
                continue
            getattr(self, cmd)(chat_id, *args)

    ### COMMANDS ###

    def help(self, chat_id):
        pass
            
    def hello(self, chat_id):
        self.send_message(chat_id, "Hello World! :)")

    def new(self, chat_id, qualifier, *args):
        if qualifier == "member": # ("member", "Full Name", "section", contact, status, *aliases)
            self.db.add_member(*args)
            self.send_message(chat_id, "Member {} added.".format(args[0]))
        if qualifier == "alias": # ("alias", "Alias", *aliases)
            self.db.add_alias(*args)
            self.send_message(chat_id, "Aliases {} registered to {}.".format(args[1:], args[0]))
        if qualifier == "practice": # ("practice", year, month, day, hour, min)
            dts = algorithm.DTS(*args)
            self.db.add_session(dts)
            self.send_message(chat_id, "Practice on {} added.".format(dts.to_datestr()))
                                                                    
    def delete(self, chat_id, qualifier, *args):
        if qualifier == "member": # ("member", "Full Name")
            self.db.delete_member(*args)
            self.send_message(chat_id, "Member {} deleted.".format(args[0]))
        if qualifier == "alias": # ("alias", *aliases)
            self.db.delete_alias(*args)
            self.send_message(chat_id, "Aliases {} deleted.".format(args))
        if qualifier == "practice": # ("practice", year, month, day[, hour, min])
            dts = algorithm.DTS(*args)
            self.db.delete_session(dts)
            self.send_message(chat_id, "Practice on {} deleted.".format(dts.to_datestr()))

    def edit(self, chat_id, qualifier, *args):
        if qualifier == "name": # ("name", "old name", "new name", *aliases)
            self.db.update_name(*args)
        if qualifier == "section": # ("section", "Full Name", "section")
            self.db.update_section(*args)
        if qualifier == "contact": # ("contact", "Full Name", "contact")
            self.db.update_contact(*args)
        if qualifier == "status": # ("status", "Full Name", "status")
            self.db.update_status(*args)
        self.send_message(chat_id, "Member {} updated.".format(args[0]))


    ### FUNCTIONS BELOW ASSUME DATE SET ###

    def setdate(self, chat_id, *args):
        dts = algorithm.DTS(*args)
        self.cur_date = dts.to_dt()
        self.send_message(chat_id, "Current date is now {}.".format(dts.to_datestr()))
        
    def update(self, chat_id, alias, text):
        self.db.update_attendance(self.cur_date, alias, text)
        self.send_message(chat_id, "Attendance for {} updated.".format(alias))

    def add(self, chat_id, alias):
        cur_dt = datetime.datetime.now()
        target_dt = self.db.get_session_time(self.cur_date).to_dt()
        self.db.set_reached(self.cur_date, alias, target_dt > cur_dt)
        self.send_message(chat_id, "{} is {}.".format("late" if target > cur_dt else "ontime"))

    def late(self, chat_id, alias, reason):
        self.db.set_late(self.cur_date, alias, reason)
        self.send_message(chat_id, "Late reason for {} updated.".format(alias))

    def absent(self, chat_id, alias, reason):
        self.db.set_absent(self.cur_date, alias, reason)
        self.send_message(chat_id, "Noshow reason for {} updated.".format(alias))

    def allabsent(self, chat_id):
        self.db.set_all_absent(self.cur_date)
        self.send_message(chat_id, "Remaining absense updated.".format(alias))
        
    ### REPORT GENERATION ###

    def report(self, chat_id, section=None, mode=None):
        if section is None:
            result = self.db.get_full_report(self.cur_date)
        elif mode == "reason":
            result = self.db.get_no_late_reason_report(self.cur_date, section)
        elif mode == "noshow":
            result = self.db.get_unfilled_report(self.cur_date, section)
        self.send_message(chat_id, "Report:\n{}".format(result))

                
if __name__ == "__main__":
    main()
