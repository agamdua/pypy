from pypy.translator.goal import targetrpystonex

LOOPS = 2000000


# __________  Entry point  __________
# _____ Define and setup target _____
# _____ Run translated _____

(entry_point,
 target,
 run) = targetrpystonex.make_target_definition(LOOPS, "normal")
