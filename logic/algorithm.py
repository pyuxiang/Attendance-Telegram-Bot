# TODO: add functionality to activate/deactivate status of past members

import sqlite3
import json
import bktree
import os
import datetime

class DT:
    def __init__(self, *args):
        """ args == datetime obj / 2018-08-20 19:47 """
        if len(args) >= 1 and type(args[0]) is str:
            # Parse datestring 2018-08-20
            self.y, self.m, self.d = list(map(int, args[0].split("-")))
            self.h, self.min = 0, 0
        if len(args) == 2 and type(args[1]) is str:
            # Parse timestring 19:47
            self.h, self.min = list(map(int, args[1].split(":")))
        if len(args) == 1 and type(args[0]) is datetime.datetime:
            dt = args[0]
            self.y, self.m, self.d, self.h, self.min = dt.year, dt.month, dt.day, dt.hour, dt.minute
            
    def to_date(self): return "{:04d}-{:02d}-{:02d}".format(self.y, self.m, self.d)
    def to_time(self): return "{:02d}:{:02d}".format(self.h, self.min)
    def to_dt(self): return datetime.datetime(self.y, self.m, self.d, self.h, self.min)
    def day_of_week(self):
        t = [0,3,2,5,0,3,5,1,4,6,2,4]
        y = self.y - (self.m < 3)
        idx = (y + y//4 - y//100 + y//400 + t[self.m-1] + self.d) % 7
        return ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday"][idx]

# only usable for backend testing
def confirm_delete():
    return input("WARNING! Deleting data... Type 'deleteme' to confirm: ") == "deleteme"

class DB:
    def __init__(self):
        self.restart()

    def restart(self):
        if not hasattr(self, "conn"):
            self.conn = sqlite3.connect("records.db", detect_types=sqlite3.PARSE_DECLTYPES)
            self.c = self.conn.cursor()
        self.initialise()
        with open("aliases.json", "r") as f:
            self.aliases = json.load(f) # alias-name pairs     
        self.alias_bktree = bktree.build(self.aliases.keys())

    def commit(self):
        self.conn.commit()
        with open("aliases.json", "w") as f:
            json.dump(self.aliases, f)

    def initialise(self):
        self.c.execute(""" CREATE TABLE IF NOT EXISTS details
                           (id INTEGER PRIMARY KEY NOT NULL,
                            name TEXT,
                            section TEXT,
                            contact INTEGER,
                            status TEXT) """)
        self.c.execute(""" CREATE TABLE IF NOT EXISTS attendance
                           (date TEXT,
                            time TEXT,
                            sessiontype TEXT) """)
        if not os.path.isfile("aliases.json"):
            with open("aliases.json", "w") as f:
                json.dump({}, f)

    def hard_reset(self):
        assert confirm_delete()
        self.c.execute("DROP TABLE IF EXISTS details")
        self.c.execute("DROP TABLE IF EXISTS attendance")
        if os.path.isfile("aliases.json"):
            os.remove("aliases.json")
        self.initialise()
        self.restart()


    ### EDITING TOOLS ###
        
    def add_member(self, name, section, contact, status, *aliases):
        """ Add new member to database. """
        # Check duplicate names
        self.c.execute("SELECT * FROM details WHERE name=?", (name,))
        if self.c.fetchone() is not None:
            return "{} already exists.".format(name)
        self.c.execute(""" INSERT INTO details (name, section, contact, status)
                           VALUES (?,?,?,?) """, (name, section.upper(), contact, status))
        self.c.execute("ALTER TABLE attendance ADD COLUMN '{}' TEXT".format(name))

        # Assign aliases to name -- including a default alias
        self.__create_new_alias(name, name)
        for alias in aliases: self.__create_new_alias(name, alias)
        self.commit()
        return "{} added.".format(name)

    def update_member(self, name, **info):
        att_headers = self.get_table_headers("attendance")
        if name not in att_headers:
            return "{} not found.".format(name)
        
        if "rename" in info:
            self.c.execute("UPDATE details SET name=? WHERE name=?", (info["rename"], name))
        if "section" in info:
            self.c.execute("UPDATE details SET section=? WHERE name=?", (info["section"], name))
        if "contact" in info:
            self.c.execute("UPDATE details SET contact=? WHERE name=?", (info["contact"], name))
        if "status" in info:
            self.c.execute("UPDATE details SET status=? WHERE name=?", (info["status"], name))
        self.commit()
        return "{} updated.".format(name)

    def update_status(self, name, status): return self.update_member(name, status=status)
    def update_contact(self, name, contact): return self.update_member(name, contact=contact)
    def update_section(self, name, section): return self.update_member(name, section=section.upper())
    def update_name(self, name, rename, *aliases):
        r = self.update_member(name, rename=rename)
        
        # Remove existing alias listings
        for key in list(self.aliases.keys()):
            if self.aliases[key] == name:
                del self.aliases[key]

        # New alias listings
        name = rename
        self.__create_new_alias(name, name)
        for alias in aliases: self.__create_new_alias(name, alias)
        self.commit()
        self.restart()
        return r

    def delete_member(self, name):
        att_headers = self.get_table_headers("attendance")
        if name not in att_headers:
            return "{} not found.".format(name)

        # Remove from attendance table (col)
        att_headers.remove(name)
        att_args = str(att_headers)[1:-1] # Argument form
        self.c.execute("CREATE TEMPORARY TABLE attendance_backup({})".format(att_args))
        self.c.execute("INSERT INTO attendance_backup SELECT {} FROM attendance".format(att_args))
        self.c.execute("DROP TABLE attendance")
        self.c.execute("CREATE TABLE attendance({})".format(att_args))
        self.c.execute("INSERT INTO attendance SELECT {} FROM attendance_backup".format(att_args))
        self.c.execute("DROP TABLE attendance_backup")

        # Remove from details table (row)
        self.c.execute("DELETE FROM details WHERE name='{}'".format(name))

        # Remove from alias data
        for key in list(self.aliases.keys()):
            if self.aliases[key] == name:
                del self.aliases[key]
        self.commit()
        self.restart()
        return "{} deleted.".format(name)
    
    def __create_new_alias(self, name, *aliases):
        for alias in aliases:
            alias = alias.replace(" ", "").lower()
            self.aliases[alias] = name
            self.alias_bktree.add(alias)

    def add_alias(self, target, *aliases):
        # TODO: Check if target is existing alias to name
        name = self.match_alias_to_name(target)
        if name == "":
            return "{} cannot be found.".format(alias)
        self.__create_new_alias(name, *aliases)
        self.commit()
        self.restart()
        return "Aliases {} added for {}.".format(aliases, name)
            
    def delete_alias(self, alias):
        alias = alias.replace(" ", "").lower()
        if alias in self.aliases:
            del self.aliases[alias]
            self.commit()
            self.restart() # Simple BKTree initialisation
            return "{} deleted.".format(alias)
        else:
            return "{} not found.".format(alias)
        


    ### PRACTICES ###

    def add_session(self, date, time, sessiontype):
        date = DT(date).to_date() # reparse
        # Works on assumption of only one practice session per day
        self.c.execute("SELECT * FROM attendance WHERE date=?", (date,))
        if self.c.fetchone() is not None:
            return "{} practice already exists.".format(date)
        self.c.execute("INSERT INTO attendance (date, time, sessiontype) VALUES (?,?,?)",
                        (date, time, sessiontype))
        self.commit()
        return "{} {} {} practice created.".format(date, time, sessiontype)

    def delete_session(self, date):
        date = DT(date).to_date() # reparse
        self.c.execute("SELECT * FROM attendance WHERE date=?", (date,))
        if self.c.fetchone() is None:
            return "{} practice not found.".format(date)
        self.c.execute("DELETE FROM attendance WHERE date=?", (date,))
        self.commit()
        return "{} practice deleted.".format(date)

    def get_session_time(self, date): # Not used
        date = DT(date).to_date() # reparse
        self.c.execute("SELECT time FROM attendance WHERE date=?", (date,))
        time_ary = self.c.fetchone()
        if time_ary is None:
            return "00:00"
            return "{} practice does not exist.".format(date)
        return time_ary[0]

    def get_session_dt(self, date): # Watch out for difference in outputs
        date = DT(date).to_date() # reparse
        self.c.execute("SELECT time FROM attendance WHERE date=?", (date,))
        time_ary = self.c.fetchone()
        if time_ary is None:
            return DT(date).to_dt()
            return "{} practice does not exist!"
        return DT(date, time_ary[0]).to_dt()


    ### UPDATE ATTENDANCE ###

    def update_attendance(self, date, alias, text):
        date = DT(date).to_date() # reparse
        name = self.match_alias_to_name(alias)
        if name == "":
            return "{} not found.".format(alias)
        self.c.execute("SELECT * FROM attendance WHERE date=?", (date,))
        if self.c.fetchone() is None:
            return "{} practice not found.".format(date)
        self.c.execute("UPDATE attendance SET '{}'='{}' WHERE date='{}'".format(name, text, date))
        self.commit()
        return "{} marked as {}.".format(name, text)

    def set_present(self, date, alias):
        date = DT(date).to_date() # reparse
        return self.update_attendance(date, alias, "present")

    def set_late(self, date, alias, reason=""):
        date = DT(date).to_date() # reparse
        text = "late" if reason == "" else ("late: " + reason)
        return self.update_attendance(date, alias, text)

    def set_absent(self, date, alias, reason=""):
        date = DT(date).to_date() # reparse
        text = "absent" if reason == "" else ("absent: " + reason)
        return self.update_attendance(date, alias, text)

    def set_absent_all(self, date):
        date = DT(date).to_date() # reparse
        self.c.execute("SELECT * FROM attendance WHERE date=?", (date,))
        if self.c.fetchone() is None:
            return "{} practice not found.".format(date)
        for member in list(self.get_not_present_report(date).keys()):
            self.c.execute("UPDATE attendance SET '{}'='absent' WHERE date='{}'".format(member, date))
        self.commit()
        return "Absence marked for {} practice.".format(date)


    ### GENERATE ATTENDANCE OVERVIEW ###

    def get_section_members(self, section):
        self.c.execute("SELECT name FROM details WHERE section LIKE '{}%'".format(section.upper()))
        return str(list(map(lambda x: x[0], self.c.fetchall())))

    def get_no_reason_report(self, date, section="."):
        return self.get_report(date, "reason", section)

    def get_not_present_report(self, date, section="."):
        return self.get_report(date, "absent", section)

    def get_full_report(self, date, section="."):
        return self.get_report(date, "full", section)
        
    def get_report(self, date, mode="full", section="."):
        date = DT(date).to_date() # reparse
        self.c.execute("SELECT * FROM attendance WHERE date=?", (date,))
        att_result = self.c.fetchone()
        if att_result is None:
            return "{} practice not found.".format(date)
        att_namelist = self.get_table_headers("attendance")

        att_list = {}
        if section != ".":
            section_members = self.get_list_of_section_members(section)
        for i in range(3, len(att_result)):
            if section != "." and att_namelist[i] not in section_members: continue
            if mode == "absent" and att_result[i] != None: continue
            if mode == "reason" and att_result[i] not in ("late", "absent"): continue
            att_list[att_namelist[i]] = att_result[i]
        return str(att_list)

    
        
        
    ### QUERY TOOLS ###

    def __match_alias(self, query):
        """ Returns a list of alias candidates """
        query = query.replace(" ", "").lower()
        if query in self.aliases: return [query]
        return self.alias_bktree.search(query)
    
    def match_alias_to_name(self, query):
        """ Returns a string representing name """
        candidates = self.__match_alias(query)
        if len(candidates) == 0: return "" # Failed to match any
        if len(candidates) == 1: return self.aliases[candidates[0]]
        possible_names = set(self.aliases[c] for c in candidates)
        if len(possible_names) == 1: return possible_names.pop()
        return "" # Failed to match unique
    

    ### TOOLS ###

    def get_table_headers(self, database):
        self.c.execute("SELECT * FROM {}".format(database))
        return list(next(zip(*self.c.description)))
        
    def print(self, database=None):
        if database in ("details", "attendance"):
            self.c.execute("SELECT * FROM {}".format(database))
            print(next(zip(*self.c.description)))
            for row in self.c: print(row)
        elif database == "alias":
            print(self.aliases)
        else:
            result = "--------------------\n"
            for database in ("details", "attendance"):
                self.c.execute("SELECT * FROM {}".format(database))
                result += str(next(zip(*self.c.description))) + "\n"
                for row in self.c: result += str(row) + "\n"
                result += "\n"
            result += str(self.aliases) + "\n"
            result += "--------------------"
        return result
                       

if __name__ == "__main__":
    db = DB()
