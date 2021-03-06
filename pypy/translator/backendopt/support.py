import py
from pypy.rpython.lltypesystem import lltype
from pypy.translator.simplify import get_graph
from pypy.rpython.rmodel import inputconst 
from pypy.tool.ansi_print import ansi_log
from pypy.annotation.model import s_ImpossibleValue
from pypy.translator.unsimplify import split_block, copyvar, insert_empty_block
from pypy.objspace.flow.model import Constant, Variable, SpaceOperation, c_last_exception
from pypy.rpython.lltypesystem import lltype


log = py.log.Producer("backendopt")
py.log.setconsumer("backendopt", ansi_log)


def graph_operations(graph):
    for block in graph.iterblocks():
        for op in block.operations: 
            yield op

def all_operations(graphs):
    for graph in graphs:
        for block in graph.iterblocks():
            for op in block.operations: 
                yield op

def annotate(translator, func, result, args):
    args   = [arg.concretetype for arg in args]
    graph  = translator.rtyper.annotate_helper(func, args)
    fptr   = lltype.functionptr(lltype.FuncType(args, result.concretetype), func.func_name, graph=graph)
    c      = inputconst(lltype.typeOf(fptr), fptr) 
    return c

def var_needsgc(var):
    if hasattr(var, 'concretetype'):
        vartype = var.concretetype
        return isinstance(vartype, lltype.Ptr) and vartype._needsgc()
    else:
        # assume PyObjPtr
        return True

def find_calls_from(translator, graph, memo=None):
    if memo and graph in memo:
        return memo[graph]
    res = [i for i in _find_calls_from(translator, graph)]
    if memo is not None:
        memo[graph] = res
    return res

def _find_calls_from(translator, graph):
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == "direct_call":
                called_graph = get_graph(op.args[0], translator)
                if called_graph is not None:
                    yield block, called_graph
            if op.opname == "indirect_call":
                graphs = op.args[-1].value
                if graphs is not None:
                    for called_graph in graphs:
                        yield block, called_graph

def find_backedges(graph, block=None, seen=None, seeing=None):
    """finds the backedges in the flow graph"""
    backedges = []
    if block is None:
        block = graph.startblock
    if seen is None:
        seen = {block: None}
    if seeing is None:
        seeing = {}
    seeing[block] = True
    for link in block.exits:
        if link.target in seen:
            if link.target in seeing:
                backedges.append(link)
        else:
            seen[link.target] = None
            backedges.extend(find_backedges(graph, link.target, seen, seeing))
    del seeing[block]
    return backedges

def compute_reachability(graph):
    reachable = {}
    blocks = list(graph.iterblocks())
    # Reversed order should make the reuse path more likely.
    for block in reversed(blocks):
        reach = set()
        scheduled = [block]
        while scheduled:
            current = scheduled.pop()
            for link in current.exits:
                if link.target in reachable:
                    reach.add(link.target)
                    reach = reach | reachable[link.target]
                    continue
                if link.target not in reach:
                    reach.add(link.target)
                    scheduled.append(link.target)
        reachable[block] = reach
    return reachable

def find_loop_blocks(graph):
    """find the blocks in a graph that are part of a loop"""
    loop = {}
    reachable = compute_reachability(graph)
    for backedge in find_backedges(graph):
        start = backedge.target
        end = backedge.prevblock
        loop[start] = start
        loop[end] = start
        scheduled = [start]
        seen = {}
        while scheduled:
            current = scheduled.pop()
            connects = end in reachable[current]
            seen[current] = True
            if connects:
                loop[current] = start
            for link in current.exits:
                if link.target not in seen:
                    scheduled.append(link.target)
    return loop

def md5digest(translator):
    from pypy.tool.compat import md5
    graph2digest = {}
    for graph in translator.graphs:
        m = md5()
        for op in graph_operations(graph):
            m.update(op.opname + str(op.result))
            for a in op.args:
                m.update(str(a))
        graph2digest[graph.name] = m.digest()
    return graph2digest
