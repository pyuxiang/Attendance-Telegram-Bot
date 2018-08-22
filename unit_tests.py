# needed for testing modules in logic dir
import os, sys; sys.path.insert(0, os.path.join(os.getcwd(), "logic"))

from algorithm import *
from main import *

failviolently = False

def main():
    print("Running tests...")
    test_DT()
    test_TeleBot()

def _(predicate, errormsg):
    """ assert equal and continue test """
    global no_test_failure
    try:
        assert predicate, errormsg
    except AssertionError as e:
        print("Failed:", e)
        no_test_failure = False

def test_result(f):
    def wrapper(*args, **kwargs):
        global no_test_failure
        no_test_failure = True
        try:
            f(*args, **kwargs)
        except Exception as e:
            if failviolently: raise e
            print("Catastrophic failure: {}".format(e))
            no_test_failure = False
        print("{} {}.".format(f.__name__, "passed" if no_test_failure else "failed"))
    return wrapper

@test_result
def test_DT():
    dt1 = DT("2018-09-13")
    dt2 = DT("2018-09-13", "19:47")
    _(dt1.to_date() == "2018-09-13", "to_date method")
    _(dt2.to_time() == "19:47", "to_time method")
    td21 = datetime.timedelta(0, 71220)
    _(dt2.to_dt() - dt1.to_dt() == td21, "datetime parsing")        

class abstractDB():

    def __init__(self):
        self.cur_dt = datetime.datetime.now()

    def add_member(self, name, section, contact, status, *aliases):
        if name == "duplicate": return "Duplicate member found!"
        if len(aliases) == 1: return "Duplicate alias found!"
        return "Member added!"

    def update_status(self, name, status):
        if name == "notfound": return "Member not found!"
        return "Status updated!"
    
    def update_contact(self, name, contact):
        if name == "notfound": return "Member not found!"
        return "Contact updated!"
    
    def update_section(self, name, section):
        if name == "notfound": return "Member not found!"
        return "Section updated!"
    
    def update_name(self, oldname, newname, *aliases):
        if oldname == "notfound": return "Member not found!"
        if newname == "duplicate": return "Duplicate member found!"
        return "Name updated!"

    def delete_member(self, name):
        if name == "notfound": return "Member not found!"
        return "Name deleted!"

    def add_alias(self, target, *aliases):
        if len(aliases) == 1: return "Duplicate alias found!"
        return "Aliases added!"

    def delete_alias(self, *aliases):
        if len(aliases) == 1: return "Duplicate alias found!"
        return "Aliases deleted!"

    # To shift datetime to DB instead of TeleBot,
    # this will also make Telebot consistent in using only string reprs... nah
    def parse_to_dt(self, date): return datetime.datetime(1970, 2, 15)
    def parse_to_date(self, dt): return "1970-02-15"
    def get_session_dt(self, date):
        assert type(date) is str
        return datetime.datetime(1971, 3, 14)
    
    def get_session_time(self, date):
        assert type(date) is str
        return "19:47"
    
    def add_session(self, date, time, sessiontype):
        assert (type(date) is str) and (type(time) is str)
        if time == "empty": return "Time not specified!"
        if date == "duplicate": return "Duplicate practice found!"
        return "Practice added!"

    def delete_session(self, date):
        assert type(date) is str
        if date == "notfound": return "Practice not found!"
        return "Practice deleted!"

    def set_dt(self, date):
        assert type(date) is str
        self.cur_dt = DT(date).to_dt()

    def set_attendance(self, date, *aliases):
        assert type(date) is str
        self.set_dt(date)
        late = self.get_session_dt(date) < self.cur_dt
        if late:
            return "\n".join(map(lambda s: self.late(self, chat_id, s), args))

    def set_present(self, date, *aliases):
        assert type(date) is str
        if date == "notfound": return "Practice not found!"
        if len(aliases) == 1: return "Duplicate alias found!"
        if len(aliases) == 2: return "Alias not found!"
        return "Set as present!"

    def set_late(self, date, alias, reason=""):
        assert type(date) is str
        if date == "notfound": return "Practice not found!"
        if alias == "notfound": return "Alias not found!"
        if reason != "": return "Set as late due reason!"
        return "Set as late!"

    def set_absent(self, date, alias, reason=""):
        assert type(date) is str
        if date == "notfound": return "Practice not found!"
        if alias == "notfound": return "Alias not found!"
        if reason != "": return "Set as absent due reason!"
        return "Set as absent!"

    def set_absent_all(self, date):
        assert type(date) is str
        if date == "notfound": return "Practice not found!"
        return "Set all as absent!"

    def set_ignore(self, date, alias):
        assert type(date) is str
        if date == "notfound": return "Practice not found!"
        if alias == "notfound": return "Alias not found!"
        return "Set as ignored!"
    
    def get_full_report(self, date, section="."): return "Full report." # to see overview of practice
    def get_no_reason_report(self, date, section="."): return "No reason report." # to update reasons
    def get_not_present_report(self, date, section="."): return "Not present report." # to update status
    def get_section_members(self, section="."): return "Member report." # for reference

@test_result
def test_TeleBot():
    bot = TeleBot(True)
    bot.send_message = print # lambda *x: x
    bot.db = abstractDB()
    def c(text):
        bot.next_offset = None
        bot.updates = {"result": [{"message":{"chat":{"id":""}, "text":text}, "update_id":2}]}
        print("\n>>> " + text)
        bot.process_updates()

    c(' /new  " alias " ali')
    c('/new')
    c('/new mem')
    c('/new member')
    c('/new member audrey')
    c('/new member duplicate sop 91234567 NUSChoir')
    c('/new member audrey sop 91234567 NUSChoir')
    c('/new member audrey s1 91234567 NUSChoir')
    c('/new member audrey s1 91234567 NUSChoir audi')
    c('/new alias audi auddi')
    c('/new alias ali ali2 ali3')
    c('/new practice 0 0')
    c('/new practice 1-1-1')
    c('/new practice 1234-5-6 12:34')
    c('/new practice 1234-5-6 1234 5')
    c('/new practice 1234-5-6 12:34 b9')
    c('/edit')
    c('/edit mem')
    c('/edit name audrey adui audi aduii')
    c('/edit section audrey')
    c('/edit section audrey s1')
    c('/edit name audrey')
    c('/edit status audrey morningsinger')
    c('/edit contact audrey 900123')
    c('/delete audrey')
    c('/delete member audrey')
    c('/delete alias audrey')
    c('/delete alias adoij asj asd')
    c('/delete practice 9-2-2 4:45')
    c('/delete practice 9-22-')
    c('/delete practice 9-2-2')
    c('/setdate 14:50')
    c('/setdate 0-0-0')
    c('/setdate 1-2-3')
    c('/add boom')
    c('/add bottle burst cloud')
    c('/present g h j')
    c('/present f')
    c('/late w')
    c('/late p reasoning')
    c('/late p politics stuff')
    c('/absent cat meow')
    c('/absentall')
    c('/report')
    c('/report .')
    c('/report . reason')
    c('/report .    ')
    c('/report sops reason')
    c('/report s reason')
    c('/report s section')
    c('/report b1 absent')
    c('/report b1 rah')
    c('/report b1 absent rah')


if __name__ == "__main__":
    main()
