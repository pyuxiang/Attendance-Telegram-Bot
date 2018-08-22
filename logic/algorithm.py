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
                            time TEXT) """)
        if not os.path.isfile("aliases.json"):
            with open("aliases.json", "w") as f:
                json.dump({}, f)

    def hard_reset(self):
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
            return "Duplicate member found!"
        self.c.execute(""" INSERT INTO details (name, section, contact, status)
                           VALUES (?,?,?,?) """, (name, section.upper(), contact, status))
        self.c.execute("ALTER TABLE attendance ADD COLUMN '{}' TEXT".format(name))

        # Assign aliases to name -- including a default alias
        self.__create_new_alias(name, name)
        for alias in aliases: self.__create_new_alias(name, alias)
        self.commit()

    def update_member(self, name, **info):
        if "rename" in info:
            self.c.execute("UPDATE details SET name=? WHERE name=?", (info["rename"], name))
        if "section" in info:
            self.c.execute("UPDATE details SET section=? WHERE name=?", (info["section"], name))
        if "contact" in info:
            self.c.execute("UPDATE details SET contact=? WHERE name=?", (info["contact"], name))
        if "status" in info:
            self.c.execute("UPDATE details SET status=? WHERE name=?", (info["status"], name))
        self.commit()

    def update_status(self, name, status): self.update_member(name, status=status)
    def update_contact(self, name, contact): self.update_member(name, contact=contact)
    def update_section(self, name, section): self.update_member(name, section=section.upper())
    def update_name(self, name, rename, *aliases):
        self.update_member(name, rename=rename)
        
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

    def delete_member(self, name):
        assert confirm_delete()

        att_headers = self.get_table_headers("attendance")
        if name not in att_headers:
            print("{} not found.".format(name))
            return

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
    
    def __create_new_alias(self, name, *aliases):
        for alias in aliases:
            alias = alias.replace(" ", "").lower()
            self.aliases[alias] = name
            self.alias_bktree.add(alias)

    def add_alias(self, target, *aliases):
        # Check if target is existing alias to name
        name = self.match_alias_to_name(target)
        if name == "":
            print("No unique name found.")
            return
        self.__create_new_alias(name, *aliases)
        self.commit()
        self.restart()
            
    def delete_alias(self, *aliases):
        for alias in aliases:
            alias = alias.replace(" ", "").lower()
            if alias in self.aliases:
                del self.aliases[alias]
            else:
                print("{} not found.".format(alias))
        self.commit()
        self.restart() # Simple BKTree initialisation


    ### PRACTICES ###

    def parse_date_as_dt(self, date):
        return DT(date).to_dt()

    def parse_dt_as_date(self, dt):
        return DT(dt).to_date()

    def get_session_dt(self, datestamp):
        pass
    
    def add_session(self, datestamp, timestamp):
        # Works on assumption of only one practice session per day
        if dts.to_timestr() == "00:00": # default value
            print("Time must be specified!")
            return
        self.c.execute("SELECT * FROM attendance WHERE date=?", (dts.to_datestr(),))
        if self.c.fetchone() is not None:
            print("Duplicate practice entries!")
            return
        self.c.execute("INSERT INTO attendance (date, time) VALUES (?,?)",
                        (dts.to_datestr(), dts.to_timestr()))
        self.commit()

    def delete_session(self, dts):
        assert confirm_delete()
        self.c.execute("DELETE FROM attendance WHERE date=?", (dts.to_datestr(),))
        self.commit()

    def get_session_time(self, dts): #datetime input
        self.c.execute("SELECT time FROM attendance WHERE data=?", (dts.to_date_str(),))
        time_ary = self.c.fetchone()
        if time_ary is None:
            print("Practice does not exist!")
            return
        dts.add_timestr(time_ary[0])
        return dts


    ### UPDATE ATTENDANCE ###

    def update_attendance(self, dts, alias, text):
        name = self.match_alias_to_name(alias)
        if name == "":
            print("{} cannot be matched.".format(alias))
            return
        self.c.execute("UPDATE attendance SET '{}'='{}' WHERE date='{}'".format(name, text, dts.to_datestr()))
        self.commit()

    def set_present(self, dts, *aliases):
        for alias in aliases:
            self.update_attendance(dts, alias, "present")

    def set_late(self, dts, alias, reason=""):
        text = "late" + ((": " + reason) if reason != "" else "")
        self.update_attendance(dts, alias, text)

    def set_absent(self, dts, alias, reason=""):
        text = "absent" + ((": " + reason) if reason != "" else "")
        self.update_attendance(dts, alias, text)

    def set_absent_all(self, dts):
        for member in list(self.get_unfilled_report(dts).keys()):
            self.c.execute("UPDATE attendance SET '{}'='NOSHOW' WHERE date='{}'".format(member, dts.to_datestr()))
            # @Problematic
            # self.c.execute("UPDATE attendance SET '{}'='NOSHOW' WHERE '{}'=NULL, date='{}'".format(member, member, dts.to_datestr()))
        self.commit()


    ### GENERATE ATTENDANCE OVERVIEW ###

    def get_no_late_reason_report(self, dts, section=None):
        return self.get_report(dts, "nolatereason", section)

    def get_unfilled_report(self, dts, section=None):
        return self.get_report(dts, "noshow", section)

    def get_full_report(self, dts, section=None):
        return self.get_report(dts, None, section)
        
    def get_report(self, dts, mode=None, section=None):
        self.c.execute("SELECT * FROM attendance WHERE date=?", (dts.to_datestr(),))
        att_result = self.c.fetchone()
        if att_result is None:
            print("No practices on {}".format(dts.to_datestr()))
            return
        att_namelist = self.get_table_headers("attendance")

        att_list = {}
        if section is not None: section_members = self.get_list_of_section_members(section)
        for i in range(2, len(att_result)):
            if section is not None and att_namelist[i] not in section_members: continue
            if mode == "noshow" and att_result[i] != None: continue
            if mode == "nolatereason" and att_result[i] not in ("LATE", "NOSHOW"): continue
            att_list[att_namelist[i]] = att_result[i]
        return att_list

    def get_list_of_section_members(self, section):
        self.c.execute("SELECT name FROM details WHERE section LIKE '{}%'".format(section.upper()))
        return list(map(lambda x: x[0], self.c.fetchall()))
        
        
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
            for database in ("details", "attendance"):
                self.c.execute("SELECT * FROM {}".format(database))
                print(next(zip(*self.c.description)))
                for row in self.c: print(row)
            print(self.aliases)
                       

if __name__ == "__main__":
    db = DB()
