import datetime

### ASSERTIONS ####
# All raised exceptions must be AssertionError to ensure
# corner cases have been caught. Sanitise data inputs.

# Generic

def count_optional_args(inputs):
    # TODO: can implement optional arg counter to recursively count optional args
    if "*" in inputs: return -1
    s, e = inputs.find("["), inputs.find("]")
    if s == -1 or e == -1: return 0
    return len(inputs[s:e].split(",")) - 1

def assert_cmd(cmd, inputs, *args):
    assert type(inputs) is str
    argc = len(inputs.split(" ")) # e.g. inputs = "member fullname section contact status[,*nicknames]"
    op_argc = count_optional_args(inputs)
    if op_argc == -1:
        assert len(args) >= argc,\
               "Expected at least {} entries instead of {},\nFormat: `/{} {}`"\
               .format(argc, len(args), cmd, inputs)
    elif op_argc == 0:
        assert len(args) == argc,\
               "Expected {} entries instead of {},\nFormat: `/{} {}`"\
               .format(argc, len(args), cmd, inputs)
    else:
        assert len(args) in (argc, argc + op_argc),\
               "Expected {} entries instead of {},\nFormat: `/{} {}`"\
               .format(argc if argc > len(args) else argc + op_argc, len(args), cmd, inputs)

# Member information

def assert_contact(contact):
    assert contact.isnumeric(), "Contact number must be numeric"

def assert_section(section):
    assert section.upper() in ("S", "S1", "S2", "A", "A1", "A2",
                               "T", "T1", "T2", "B", "B1", "B2"),\
        "Section is represented with letter and optional subsection."

def assert_attendance(remark):
    assert remark == "present"\
           or remark.startswith("late")\
           or remark.startswith("absent")

def assert_date(date):
    errormsg = "date is represented in 'YYYY-MM-DD' format"
    assert type(date) is str
    assert "-" in date, errormsg
    assert all(map(lambda x: x.isnumeric(), date.split("-"))), errormsg
    year, month, day = list(map(int, date.split("-")))
    try:
        # rely on datetime inbuilt date verification
        dt = datetime.datetime(year, month, day)
    except ValueError as e:
        raise AssertionError(str(e))

def assert_time(time):
    errormsg = "time is represented in 'HH:MM' format"
    assert type(time) is str
    assert ":" in time, errormsg
    assert all(map(lambda x: x.isnumeric(), time.split(":"))), errormsg
    hour, minute = list(map(int, time.split(":")))
    try:
        # rely on datetime inbuilt time verification
        dt = datetime.datetime(1,1,1, hour, minute)
    except ValueError as e:
        raise AssertionError(str(e))

def assert_datetime(date, time):
    assert_date(date)
    assert_time(time)
