import sqlite3
import json
import bktree
import os

class DB:
    def __init__(self):
        self.restart()

    def restart(self):
        if not hasattr(self, "conn"): self.conn = sqlite3.connect("records.db")
        if hasattr(self, "c"): self.c.close()
        self.c = self.conn.cursor()
        self.initialise()
        with open("aliases.json", "r") as f:
            self.aliases = json.load(f) # alias-name pairs     
        self.alias_bktree = bktree.build(self.aliases.keys())

    def commit(self):
        self.conn.commit()
        with open("aliases.json", "w") as f:
            json.dump(self.aliases, f)


    ### EDITING TOOLS ###
        
    def add_member(self, name, section, contact, status, *aliases):
        # Check duplicate names
        self.c.execute("SELECT * FROM details WHERE name=?", (name,))
        if self.c.fetchone() is not None:
            print("Duplicate member found!")
            return

        # Insert details into both databases
        self.c.execute(""" INSERT INTO details (name, section, contact, status)
                           VALUES (?,?,?,?) """, (name, section, contact, status))
        self.c.execute("ALTER TABLE attendance ADD COLUMN '{}' TEXT".format(name))

        # Assign aliases to name -- including a default alias
        self.__create_new_alias(name, name)
        for alias in aliases: self.__create_new_alias(name, alias)
        self.commit()

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

        ### DO NOT RESOLVE MATCHING CONFLICTS ###
        ## Alias cannot be matched - resolve matching conflict and learn
        # print("More than one {} found. Select one:\n{}"
        #       .format(space, list(enumerate(candidates))))
        # name = candidates[int(input())]
        # self.new_alias(name, alias) # pair alias with name
    

    ### DEBUGGING TOOLS ###
        
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

    def initialise(self):
        self.c.execute(""" CREATE TABLE IF NOT EXISTS details
                           (id INTEGER PRIMARY KEY NOT NULL,
                            name TEXT,
                            section TEXT,
                            contact INTEGER,
                            status TEXT) """)
        self.c.execute(""" CREATE TABLE IF NOT EXISTS attendance
                           (date date,
                            time timestamp) """)
        if not os.path.isfile("aliases.json"):
            with open("aliases.json", "w") as f:
                json.dump({}, f)

    def hard_reset(self):
        usr = input("WARNING! Deleting database... Type 'deleteme' to confirm: ")
        if usr != "deleteme": return
        
        self.c.execute("DROP TABLE IF EXISTS details")
        self.c.execute("DROP TABLE IF EXISTS attendance")
        if os.path.isfile("aliases.json"):
            os.remove("aliases.json")
        self.initialise()
        self.restart()

if __name__ == "__main__":
    db = DB()
