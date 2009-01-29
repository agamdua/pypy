
import py
from pypy.conftest import gettestobjspace, option

class PyPyOutput:
    nfunc = 127
    nprim = 107
    optional_line = '\n.*'

class CPythonOutput:
    nfunc = 126
    nprim = 106
    optional_line = ''

def match(method, pattern, string):
    import re
    if not re.match(pattern, string):
        print method, 'differs:'
        print 'Difference is here:'
        print '     GOT:', string.rstrip('\n')
        print 'EXPECTED:', pattern.rstrip('\n')
        return False
    return True

class AppTestCProfile(object):

    objspace_options = {}

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_lsprof',),
                                **cls.objspace_options)
        cls.w_expected_output = space.wrap(expected_output)
        cls.space = space
        cls.w_file = space.wrap(__file__)
        if option.runappdirect:
            output = CPythonOutput.__dict__
        else:
            output = PyPyOutput.__dict__
        cls.w_output = space.wrap(output)
        cls.w_match = space.wrap(match)

    def test_direct(self):
        import _lsprof
        def getticks():
            return len(ticks)
        prof = _lsprof.Profiler(getticks, 0.25, True, False)
        ticks = []
        def bar(m):
            ticks.append(1)
            if m == 1:
                foo(42)
            ticks.append(1)
        def spam(m):
            bar(m)
        def foo(n):
            bar(n)
            ticks.append(1)
            bar(n+1)
            ticks.append(1)
            spam(n+2)
        prof.enable()
        foo(0)
        prof.disable()
        assert len(ticks) == 16
        stats = prof.getstats()
        entries = {}
        for entry in stats:
            if not hasattr(entry.code, 'co_name'):
                print entry.code
            else:
                entries[entry.code.co_name] = entry
        efoo = entries['foo']
        assert efoo.callcount == 2
        assert efoo.reccallcount == 1
        assert efoo.inlinetime == 1.0
        assert efoo.totaltime == 4.0
        assert len(efoo.calls) == 2
        ebar = entries['bar']
        assert ebar.callcount == 6
        assert ebar.reccallcount == 3
        assert ebar.inlinetime == 3.0
        assert ebar.totaltime == 3.5
        assert len(ebar.calls) == 1
        espam = entries['spam']
        assert espam.callcount == 2
        assert espam.reccallcount == 0
        assert espam.inlinetime == 0.0
        assert espam.totaltime == 1.0
        assert len(espam.calls) == 1

        foo2spam, foo2bar = efoo.calls
        if foo2bar.code.co_name == 'spam':
            foo2bar, foo2spam = foo2spam, foo2bar
        assert foo2bar.code.co_name == 'bar'
        assert foo2bar.callcount == 4
        assert foo2bar.reccallcount == 2
        assert foo2bar.inlinetime == 2.0
        assert foo2bar.totaltime == 3.0
        assert foo2spam.code.co_name == 'spam'
        assert foo2spam.callcount == 2
        assert foo2spam.reccallcount == 0
        assert foo2spam.inlinetime == 0.0
        assert foo2spam.totaltime == 1.0

        bar2foo, = ebar.calls
        assert bar2foo.code.co_name == 'foo'
        assert bar2foo.callcount == 1
        assert bar2foo.reccallcount == 0
        assert bar2foo.inlinetime == 0.5
        assert bar2foo.totaltime == 2.0

        spam2bar, = espam.calls
        assert spam2bar.code.co_name == 'bar'
        assert spam2bar.callcount == 2
        assert spam2bar.reccallcount == 0
        assert spam2bar.inlinetime == 1.0
        assert spam2bar.totaltime == 1.0

    def test_cprofile(self):
        import sys, os
        # XXX this is evil trickery to walk around the fact that we don't
        #     have __file__ at app-level here
        sys.path.insert(0, os.path.dirname(self.file))
        try:
            import re
            from cProfile import Profile
            from profilee import testfunc, timer

            methodnames = ['print_stats', 'print_callers', 'print_callees']

            def do_profiling(cls):
                results = []
                prof = cls(timer, 0.001)
                start_timer = timer()
                prof.runctx("testfunc()", {'testfunc':testfunc}, locals())
                results.append(timer() - start_timer)
                for methodname in methodnames:
                    import pstats
                    from StringIO import StringIO
                    s = StringIO()
                    stats = pstats.Stats(prof, stream=s)
                    stats.strip_dirs().sort_stats("stdname")
                    getattr(stats, methodname)()
                    results.append(s.getvalue())
                return results, prof

            res, prof = do_profiling(Profile)
            assert res[0] == 1000
            for i, method in enumerate(methodnames):
                got = res[i + 1]
                expected = self.expected_output[method]
                expected = expected % self.output
                patterns = expected.splitlines()
                lines = got.splitlines()
                for pattern, line in zip(patterns, lines):
                    pattern = pattern.replace('(', '\\(')
                    pattern = pattern.replace(')', '\\)')
                    pattern = pattern.replace('?', '\\?')
                    if not self.match(method, pattern, line):
                        print '--- GOT ---'
                        print got
                        print
                        print '--- EXPECTED ---'
                        print expected
                        assert False
                assert len(patterns) == len(lines)
        finally:
            sys.path.pop(0)


class AppTestOptimized(AppTestCProfile):

    objspace_options = {'objspace.std.builtinshortcut': True}

    def test_cprofile(self):
        skip('fixme')

expected_output = {}
expected_output['print_stats'] = """\
         %(nfunc)d function calls (%(nprim)d primitive calls) in 1.000 CPU seconds

   Ordered by: standard name

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    1.000    1.000 <string>:1(<module>)%(optional_line)s
       28    0.028    0.001    0.028    0.001 profilee.py:110(__getattr__)
        1    0.270    0.270    1.000    1.000 profilee.py:25(testfunc)
     23/3    0.150    0.007    0.170    0.057 profilee.py:35(factorial)
       20    0.020    0.001    0.020    0.001 profilee.py:48(mul)
        2    0.040    0.020    0.600    0.300 profilee.py:55(helper)
        4    0.116    0.029    0.120    0.030 profilee.py:73(helper1)
        2    0.000    0.000    0.140    0.070 profilee.py:84(helper2_indirect)
        8    0.312    0.039    0.400    0.050 profilee.py:88(helper2)
        8    0.064    0.008    0.080    0.010 profilee.py:98(subhelper)
       12    0.000    0.000    0.012    0.001 {hasattr.*}
        4    0.000    0.000    0.000    0.000 {method 'append' of 'list' objects}
        1    0.000    0.000    0.000    0.000 {method 'disable' of '.*' objects}
        8    0.000    0.000    0.000    0.000 {range.*}
        4    0.000    0.000    0.000    0.000 {sys.exc_info.*}


"""

expected_output['print_callers'] = """\
   Ordered by: standard name

Function                             *    was called by...
                                     *        ncalls  tottime  cumtime
<string>:1(<module>)                 *    <-%(optional_line)s
profilee.py:110(__getattr__)         *    <-      16    0.016    0.016  profilee.py:98(subhelper)
                                     *            12    0.012    0.012  {hasattr.*}
profilee.py:25(testfunc)             *    <-       1    0.270    1.000  <string>:1(<module>)
profilee.py:35(factorial)            *    <-       1    0.014    0.130  profilee.py:25(testfunc)
                                     *          20/3    0.130    0.147  profilee.py:35(factorial)
                                     *             2    0.006    0.040  profilee.py:84(helper2_indirect)
profilee.py:48(mul)                  *    <-      20    0.020    0.020  profilee.py:35(factorial)
profilee.py:55(helper)               *    <-       2    0.040    0.600  profilee.py:25(testfunc)
profilee.py:73(helper1)              *    <-       4    0.116    0.120  profilee.py:55(helper)
profilee.py:84(helper2_indirect)     *    <-       2    0.000    0.140  profilee.py:55(helper)
profilee.py:88(helper2)              *    <-       6    0.234    0.300  profilee.py:55(helper)
                                     *             2    0.078    0.100  profilee.py:84(helper2_indirect)
profilee.py:98(subhelper)            *    <-       8    0.064    0.080  profilee.py:88(helper2)
{hasattr.*}           * <-       4    0.000    0.004  profilee.py:73(helper1)
                      *          8    0.000    0.008  profilee.py:88(helper2)
{method 'append' .*}  * <-       4    0.000    0.000  profilee.py:73(helper1)
{method 'disable' .*} * <-
{range.*}             * <-       8    0.000    0.000  profilee.py:98(subhelper)
{sys.exc_info.*}      * <-       4    0.000    0.000  profilee.py:73(helper1)


"""
expected_output['print_callees'] = """\
   Ordered by: standard name

Function                         * called...
                                 *     ncalls  tottime  cumtime
<string>:1(<module>)             * ->       1    0.270    1.000  profilee.py:25(testfunc)%(optional_line)s
profilee.py:110(__getattr__)     * ->
profilee.py:25(testfunc)         * ->       1    0.014    0.130  profilee.py:35(factorial)
                                 *          2    0.040    0.600  profilee.py:55(helper)
profilee.py:35(factorial)        * ->    20/3    0.130    0.147  profilee.py:35(factorial)
                                 *         20    0.020    0.020  profilee.py:48(mul)
profilee.py:48(mul)              * ->
profilee.py:55(helper)           * ->       4    0.116    0.120  profilee.py:73(helper1)
                                 *          2    0.000    0.140  profilee.py:84(helper2_indirect)
                                 *          6    0.234    0.300  profilee.py:88(helper2)
profilee.py:73(helper1)          * ->       4    0.000    0.004  {hasattr.*}
                                 *          4    0.000    0.000  {method 'append' of 'list' objects}
                                 *          4    0.000    0.000  {sys.exc_info.*}
profilee.py:84(helper2_indirect) * ->       2    0.006    0.040  profilee.py:35(factorial)
                                 *          2    0.078    0.100  profilee.py:88(helper2)
profilee.py:88(helper2)          * ->       8    0.064    0.080  profilee.py:98(subhelper)
                                 *          8    0.000    0.008  {hasattr.*}
profilee.py:98(subhelper)        * ->      16    0.016    0.016  profilee.py:110(__getattr__)
                                 *          8    0.000    0.000  {range.*}
{hasattr.*}           * ->      12    0.012    0.012  profilee.py:110(__getattr__)
{method 'append' .*}  * ->
{method 'disable' .*} * ->
{range.*}             * ->
{sys.exc_info.*}      * ->


"""
